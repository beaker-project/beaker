#!/usr/bin/python

import hashlib
import base64
import xmlrpclib
import time
from lxml import etree
from socket import gethostname


class BeahDummy(object):

    install_time = 600 #seconds
    task_duration = 120 # seconds
    task_log_chunk = 'thisisdummydata' * 66
    task_log_chunk_enc = base64.encodestring(task_log_chunk)
    task_log_chunk_md5 = hashlib.md5(task_log_chunk).hexdigest()
    task_log_chunk_count = 128
    recipe_log = 'thisisdummydata' * 326
    recipe_log_enc = base64.encodestring(recipe_log)
    recipe_log_md5 = hashlib.md5(recipe_log).hexdigest()

    def __init__(self, machine_name, proxy_hostname='localhost'):
        self.machine_name = machine_name
        self.rpc2 = xmlrpclib.ServerProxy('http://%s:8000/RPC2' % proxy_hostname)

    def run(self):
        print '%s install_start' % self.machine_name
        self.rpc2.install_start(self.machine_name)
        time.sleep(self.install_time) #install time
        recipe = self.rpc2.get_recipe(self.machine_name)
        tree = etree.fromstring(recipe)
        for task in tree.findall('.//task'):
            task_id = task.get('id')
            task_name = task.get('name')
            self.run_task(task_id, task_name)

    def run_task(self, task_id, task_name):
        """
        Start the task, send some logs, sleep a bit for the runtime, the send pass result
        and stop the task

        """
        offset_task_log = 0
        print '%s T:%s task_start' % (self.machine_name, task_id)
        self.rpc2.task_start(task_id)
        for i in xrange(self.task_log_chunk_count):
            print '%s T:%s task_upload_file' % (self.machine_name, task_id)
            self.rpc2.task_upload_file(task_id, 'load_test',
                    'name_%s' % task_id, len(self.task_log_chunk), self.task_log_chunk_md5,
                    offset_task_log, self.task_log_chunk_enc)
            offset_task_log += len(self.task_log_chunk)

        #final chunk
        print '%s T:%s task_upload_file' % (self.machine_name, task_id)
        self.rpc2.task_upload_file(task_id, 'load_test', 'name_%s' % task_id, 
            len(self.task_log_chunk), self.task_log_chunk_md5, -1, self.task_log_chunk_enc)
        #Simulate some run time
        time.sleep(self.task_duration)
        #send result
        print '%s T:%s task_result' % (self.machine_name, task_id)
        result_id = self.rpc2.task_result(task_id, 'pass_', task_name, '1079',
            '(Pass)')
        #no chunking
        print '%s T:%s TR:%s result_upload_file' % (self.machine_name, task_id, result_id)
        self.rpc2.result_upload_file(result_id, '/',
            'load_test--result', len(self.recipe_log), self.recipe_log_md5, 0, self.recipe_log_enc)
        print '%s T:%s task_stop' % (self.machine_name, task_id)
        self.rpc2.task_stop(task_id, 'stop', 'OK')

class BeahDummyManager(object):

    """
    It's too expensive to create a separate beah_dummy process for potentially 
    thousands of dummy systems at the same time. So this is a tiny server 
    process which runs multiple beah_dummies in their own greenlet.

    To start a new beah_dummy:
        PUT /beah_dummy/fqdn.example.com
    """

    # TODO we could also implement DELETE to terminate a running beah_dummy

    def wsgi(self, environ, start_response):
        if not environ['PATH_INFO'].startswith('/beah_dummy/'):
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return ['Path %s does not exist' % environ['PATH_INFO']]
        if environ['REQUEST_METHOD'] != 'PUT':
            start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
            return ['Method %s is not allowed' % environ['REQUEST_METHOD']]
        hostname = environ['PATH_INFO'][len('/beah_dummy/'):]
        gevent.spawn(BeahDummy(hostname).run)
        start_response('204 No Content', [])
        return []

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    opts, args = parser.parse_args()
    if not opts.foreground:
        import daemon
        daemon.DaemonContext().open()
    import gevent.monkey
    gevent.monkey.patch_all(thread=False)
    from gevent.pywsgi import WSGIServer
    WSGIServer(('', 8001), BeahDummyManager().wsgi).serve_forever()
