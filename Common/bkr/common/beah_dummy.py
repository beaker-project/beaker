import hashlib
import base64
import xmlrpclib
import time
import threading
import logging
from lxml import etree
from StringIO import StringIO
from socket import gethostname

log = logging.getLogger(__name__)


class BeahDummy(threading.Thread):

    _dummy_string = 'thisisdummydata'

    _file_size = 512000 # bytes
    _install_time = 30

    def __init__(self, machine_name, proxy_addr=None, *args, **kw):
        super(BeahDummy,self).__init__(*args, **kw)
        self.machine_name = machine_name
        if not proxy_addr:
            proxy_addr = gethostname()
        self.rpc2 = xmlrpclib.ServerProxy('http://%s:8000/RPC2' % proxy_addr)

    def run(self):
        self.rpc2.install_start(self.machine_name)
        log.info('Seeping for %s seconds' % self._install_time)
        time.sleep(self._install_time) #install time
        recipe = self.rpc2.get_recipe(self.machine_name)
        tree = etree.parse(StringIO(recipe))
        for task in tree.findall('//task'):
            task_id = task.get('id')
            task_name = task.get('name')
            self.run_task(task_id, task_name)

    def run_task(self, task_id, task_name):
        """

        i.e duration = 1 hour
        files = 10
        size = 20k

        """
        string_to_send = self._dummy_string * 66 # testing with this chunk size
        chunk_size = len(string_to_send)
        total_size_sent_task_log = 0
        offset_task_log = 0
        self.rpc2.task_start(task_id)
        _md5 = hashlib.md5()
        _md5.update(string_to_send)
        while total_size_sent_task_log < self._file_size:
            data = base64.encodestring(string_to_send)
            self.rpc2.task_upload_file(task_id, 'load_test',
            'name_%s' % task_id, chunk_size, _md5.hexdigest(),
            offset_task_log, data)
            offset_task_log += 1
            total_size_sent_task_log += chunk_size

        #final chunk
        self.rpc2.task_upload_file(task_id, 'load_test', 'name_%s' % task_id, 
            chunk_size, _md5.hexdigest(), -1, data)
       
        #send result
        result_id = self.rpc2.task_result(task_id, 'pass_', task_name, '1079',
            '(Pass)')
        offset_result_log = 0
        total_size_sent_result_log = 0
        string_to_send_result = self._dummy_string * 326
        result_data = base64.encodestring(string_to_send_result)
        #no chunking
        self.rpc2.result_upload_file(result_id, '/',
            'load_test--result', len(string_to_send_result), '', '0', result_data)
        self.rpc2.task_stop(task_id, 'stop', 'OK')
