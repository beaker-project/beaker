import errno
import os
import sys
import logging
import signal
import time
import datetime
from xmlrpclib import Fault, ProtocolError
from cStringIO import StringIO
from socket import gethostbyaddr

import kobo.conf
from kobo.client import HubProxy
from kobo.exceptions import ShutdownException

from kobo.process import kill_process_group
from kobo.log import add_rotating_file_logger

class ProxyHelper(object):

    def __init__(self, logger=None, conf=None, **kwargs):
        self.conf = kobo.conf.PyConfigParser()

        # load default config
        default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
        self.conf.load_from_file(default_config)

        # update data from another config
        if conf is not None:
            self.conf.load_from_conf(conf)

        # update data from config specified in os.environ
        conf_environ_key = "BEAKER_PROXY_CONFIG_FILE"
        if conf_environ_key in os.environ:
            self.conf.load_from_file(os.environ[conf_environ_key])

        self.conf.load_from_dict(kwargs)

        # setup logger
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger("Proxy")
            self.logger.setLevel(logging.DEBUG)
            log_level = logging._levelNames.get(self.conf["LOG_LEVEL"].upper())
            log_file = self.conf["LOG_FILE"]
            add_rotating_file_logger(self.logger, log_file, log_level=log_level)

        # self.hub is created here
        self.hub = HubProxy(logger=self.logger, conf=self.conf, **kwargs)

    def task_result(self, 
                    task_id, 
                    result_type, 
                    result_path=None, 
                    result_score=None,
                    result_summary=None):
        """ report a result to the scheduler """
        return self.hub.recipes.tasks.result(task_id,
                                             result_type,
                                             result_path,
                                             result_score,
                                             result_summary)

    def recipe_stop(self,
                    recipe_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this recipe
            stop_type = ['abort', 'cancel']
            msg to record
        """
        return self.hub.recipes.stop(recipe_id, stop_type, msg)

    def job_stop(self,
                    job_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this job
            stop_type = ['abort', 'cancel']
            msg to record 
        """
        return self.hub.jobs.stop(job_id, stop_type, msg)


class Watchdog(ProxyHelper):

    watchdogs = dict()

    def recipe_upload_file(self, 
                         recipe_id, 
                         path, 
                         name, 
                         size, 
                         md5sum, 
                         offset, 
                         data):
        """ Upload a file in chunks
             path: the relative path to upload to
             name: the name of the file
             size: size of the contents (bytes)
             md5: md5sum (hex digest) of contents
             data: base64 encoded file contents
             offset: the offset of the chunk
            Files can be uploaded in chunks, if so the md5 and the size 
            describe the chunk rather than the whole file.  The offset
            indicates where the chunk belongs
            the special offset -1 is used to indicate the final chunk
        """
        return self.hub.recipes.upload_file(recipe_id, 
                                            path, 
                                            name, 
                                            size, 
                                            md5sum, 
                                            offset, 
                                            data)

    def monitor_forever(self):
        while True:
            # Clear out expired watchdog entries
            for watchdog in self.hub.recipes.tasks.watchdogs(status='expired'):
                self.abort(watchdog)

            # Monitor active watchdog entries
            for watchdog in self.hub.recipes.tasks.watchdogs(status='active'):
                self.monitor(watchdog)
            # Sleep 20 seconds between polling
            time.sleep(20)

    def abort(self, watchdog):
        """ Abort expired watchdog entry
        """
        # Check to see if we have an active monitor running and kill it.
        if watchdog['system'] in self.watchdogs:
            try:
                kill_process_group(self.watchdogs[watchdog['system']],
                                   logger=self.logger)
            except IOError, ex:
                # proc file doesn't exist -> process was already killed
                pass
            del self.watchdogs[watchdog['system']]
        self.recipe_stop(watchdog['recipe_id'], 'External Watchdog Expired')

    def monitor(self, watchdog):
        """ Upload console log if present to Scheduler
             and look for panic/bug/etc..
        """
        if watchdog['system'] not in self.watchdogs:
            self.logger.info("Create monitor for %s" % watchdog['system'])
            #pid = #FIXME Create Monitor(conf=conf, watchdog['system'])
            #self.watchdogs[watchdog['system']] = pid


class Proxy(ProxyHelper):
    def get_recipe(self, system_name=None):
        """ return the active recipe for this system 
            If system_name is not provided look up via client_ip"""
        if not system_name:
            system_name = gethostbyaddr(self.clientIP)[0]
        return self.hub.recipes.system_xml(system_name)

    def task_upload_file(self, 
                         task_id, 
                         path, 
                         name, 
                         size, 
                         md5sum, 
                         offset, 
                         data):
        """ Upload a file in chunks
             path: the relative path to upload to
             name: the name of the file
             size: size of the contents (bytes)
             md5: md5sum (hex digest) of contents
             data: base64 encoded file contents
             offset: the offset of the chunk
            Files can be uploaded in chunks, if so the md5 and the size 
            describe the chunk rather than the whole file.  The offset
            indicates where the chunk belongs
            the special offset -1 is used to indicate the final chunk
        """
        return self.hub.recipes.tasks.upload_file(task_id, 
                                                  path, 
                                                  name, 
                                                  size, 
                                                  md5sum, 
                                                  offset, 
                                                  data)

    def task_start(self,
                   task_id,
                   kill_time=None):
        """ tell the scheduler that we are starting a task
            default watchdog time can be overridden with kill_time seconds """
        return self.hub.recipes.tasks.start(task_id, kill_time)


    def task_stop(self,
                  task_id,
                  stop_type,
                  msg=None):
        """ tell the scheduler that we are stoping a task
            stop_type = ['stop', 'abort', 'cancel']
            msg to record if issuing Abort or Cancel """
        return self.hub.recipes.tasks.stop(task_id, stop_type, msg)
