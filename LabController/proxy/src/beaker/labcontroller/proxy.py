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

from kobo.log import add_rotating_file_logger


class Proxy(object):
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

    def get_recipe(self, system_name=None):
        """ return the active recipe for this system 
            If system_name is not provided look up via client_ip"""
        if not system_name:
            system_name = gethostbyaddr(self.clientIP)[0]
        return self.hub.recipes.system_xml(system_name)

    def upload_file(self, path, name, size, md5sum, offset, data):
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
        return self.hub.recipes.tasks.upload_file(path, 
                                                  name, 
                                                  size, 
                                                  md5sum, 
                                                  offset, 
                                                  data)

    def task_start(self,
                   task_id,
                   kill_time):
        """ tell the scheduler that we are starting a task
            default watchdog time can be overridden with kill_time seconds """
        return self.hub.recipes.tasks.Start(task_id, kill_time)

    def task_result(self, 
                    task_id, 
                    result_type, 
                    result_path, 
                    result_score,
                    result_summary):
        """ report a result to the scheduler """
        return self.hub.recipes.tasks.Result(task_id,
                                             result_type,
                                             result_path,
                                             result_score,
                                             result_summary)

    def task_stop(self,
                  task_id,
                  stop_type,
                  msg):
        """ tell the scheduler that we are stoping a task
            stop_type = ['Stop', 'Abort', 'Cancel']
            msg to record if issuing Abort or Cancel """
        return self.hub.recipes.tasks.Stop(task_id, stop_type, msg)
