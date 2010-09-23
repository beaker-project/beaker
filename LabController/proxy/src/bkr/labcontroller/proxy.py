import errno
import os
import sys
import logging
import signal
import time
import datetime
import base64
import xmltramp
import glob
import re
from xmlrpclib import Fault, ProtocolError
from cStringIO import StringIO
from socket import gethostbyaddr

import kobo.conf
from kobo.client import HubProxy
from kobo.exceptions import ShutdownException

from kobo.process import kill_process_group
from kobo.log import add_rotating_file_logger

try:
    from hashlib import md5 as md5_constructor
except ImportError:
    from md5 import new as md5_constructor

VERBOSE_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] {%(process)5d} %(name)s.%(module)s:%(lineno)4d %(message)s"

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
            add_rotating_file_logger(self.logger, 
                                     log_file, 
                                     log_level=log_level,
                                     format=VERBOSE_LOG_FORMAT)

        # self.hub is created here
        self.hub = HubProxy(logger=self.logger, conf=self.conf, **kwargs)

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
        self.logger.info("recipe_upload_file recipe_id:%s name:%s offset:%s size:%s" % (recipe_id, 
                                                                                        name,
                                                                                        offset,
                                                                                        size))
        return self.hub.recipes.upload_file(recipe_id, 
                                            path, 
                                            name, 
                                            size, 
                                            md5sum, 
                                            offset, 
                                            data)

    def task_result(self, 
                    task_id, 
                    result_type, 
                    result_path=None, 
                    result_score=None,
                    result_summary=None):
        """ report a result to the scheduler """
        self.logger.info("task_result %s" % task_id)
        return self.hub.recipes.tasks.result(task_id,
                                             result_type,
                                             result_path,
                                             result_score,
                                             result_summary)

    def task_info(self,
                  qtask_id):
        """ accepts qualified task_id J:213 RS:1234 R:312 T:1234 etc.. Returns dict with status """
        self.logger.info("task_info %s" % qtask_id)
        return self.hub.taskactions.task_info(qtask_id)

    def recipe_stop(self,
                    recipe_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this recipe
            stop_type = ['abort', 'cancel']
            msg to record
        """
        self.logger.info("recipe_stop %s" % recipe_id)
        return self.hub.recipes.stop(recipe_id, stop_type, msg)

    def recipeset_stop(self,
                    recipeset_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this recipeset
            stop_type = ['abort', 'cancel']
            msg to record
        """
        self.logger.info("recipeset_stop %s" % recipeset_id)
        return self.hub.recipesets.stop(recipeset_id, stop_type, msg)

    def job_stop(self,
                    job_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this job
            stop_type = ['abort', 'cancel']
            msg to record 
        """
        self.logger.info("job_stop %s" % job_id)
        return self.hub.jobs.stop(job_id, stop_type, msg)

    def get_recipe(self, system_name=None):
        """ return the active recipe for this system """
        if system_name:
            self.logger.info("get_recipe %s" % system_name)
            return self.hub.recipes.system_xml(system_name)

    def extend_watchdog(self, task_id, kill_time):
        """ tell the scheduler to extend the watchdog by kill_time seconds
        """
        self.logger.info("extend_watchdog %s %s", task_id, kill_time)
        return self.hub.recipes.tasks.extend(task_id, kill_time)

    def task_to_dict(self, task_name):
        """ returns metadata about task_name from the TaskLibrary 
        """
        return self.hub.tasks.to_dict(task_name)


class WatchFile(object):
    """
    Helper class to watch log files and upload them to Scheduler
    """

    def __init__(self, log, watchdog, proxy, panic, blocksize=65536):
        self.log = log
        self.watchdog = watchdog
        self.proxy = proxy
        self.blocksize = blocksize
        self.filename = os.path.basename(self.log)
        # If filename is the hostname then rename it to console.log
        if self.filename == self.watchdog['system']:
            self.filename="console.log"
            # Leave newline
            self.control_chars = ''.join(map(unichr, range(0,9) + range(11,32) + range(127,160)))
            self.strip_ansi = re.compile('[%s]' % re.escape(self.control_chars))
            self.panic = re.compile(r'%s' % panic)
        else:
            self.strip_ansi = None
            self.panic = None
        self.where = 0

    def __cmp__(self,other):
        """
        Used to compare logs that are already being watched.
        """
        if self.log == other:
            return 0
        else:
            return 1

    def update(self):
        """
        If the log exists and the file has grown then upload the new piece
        """
        if os.path.exists(self.log):
            file = open(self.log, "r")
            where = self.where
            file.seek(where)
            line = file.read(self.blocksize)
            size = len(line)
            if self.strip_ansi:
                line = self.strip_ansi.sub(' ',line.decode('ascii', 'replace').encode('ascii', 'replace'))
            now = file.tell()
            file.close()
            if self.panic:
                # Search the line for panics
                # The regex is stored in /etc/beaker/proxy.conf
                panic = self.panic.search(line)
                if panic:
                    self.proxy.logger.info("Panic detected for system: %s" % self.watchdog['system'])
                    recipeset = xmltramp.parse(self.proxy.get_recipe(self.watchdog['system'])).recipeSet
                    try:
                        recipe = recipeset.recipe
                    except AttributeError:
                        recipe = recipeset.guestrecipe
                    watchdog = recipe.watchdog()
                    if 'panic' in watchdog and watchdog['panic'] == 'ignore':
                        # Don't Report the panic
                        self.proxy.logger.info("Not reporting panic, recipe set to ignore")
                    else:
                        # Report the panic
                        # Look for active task, worst case it records it on the last task
                        for task in recipe['task':]:
                            if task()['status'] == 'Running':
                                break
                        self.proxy.task_result(task()['id'], 'panic', '/', 0, panic.group())
                        # set the watchdog timeout to 10 seconds, gives some time for all data to 
                        # print out on the serial console
                        # this may abort the recipe depending on what the recipeSets
                        # watchdog behaviour is set to.
                        self.proxy.extend_watchdog(self.watchdog['task_id'], 10)
            if not line:
                return False
            # If we didn't read our full blocksize and we are still growing
            #  then don't send anything yet.
            elif size < self.blocksize and where == now:
                return False
            else:
                self.where = now
                data = base64.encodestring(line)
                md5sum = md5_constructor(line).hexdigest()
                self.proxy.recipe_upload_file(self.watchdog['recipe_id'],
                                             "/",
                                             self.filename,
                                             size,
                                             md5sum,
                                             where,
                                             data)
                return True


class Watchdog(ProxyHelper):

    watchdogs = dict()

    def expire_watchdogs(self):
        """Clear out expired watchdog entries"""

        for watchdog in self.hub.recipes.tasks.watchdogs('expired'):
            self.abort(watchdog)

    def active_watchdogs(self):
        """Monitor active watchdog entries"""

        active_watchdogs = []
        for watchdog in self.hub.recipes.tasks.watchdogs('active'):
            active_watchdogs.append(watchdog['system'])
            if watchdog['system'] not in self.watchdogs:
                self.watchdogs[watchdog['system']] = Monitor(watchdog,self.logger,self.conf)
        # Remove Monitor if watchdog does not exist.
        for watchdog_system in self.watchdogs.copy():
            if watchdog_system not in active_watchdogs:
                del self.watchdogs[watchdog_system]
                self.logger.info("Removed Monitor for %s" % watchdog_system)
        updated = False
        for monitor in self.watchdogs:
            if self.watchdogs[monitor].run():
                updated = True
        return updated

    def sleep(self):
        # Sleep between polling
        time.sleep(self.conf.get("SLEEP_TIME", 20))

    def abort(self, watchdog):
        """ Abort expired watchdog entry
        """
        self.logger.info("External Watchdog Expired for %s" % watchdog['system'])
        self.recipe_stop(watchdog['recipe_id'],
                         'abort', 
                         'External Watchdog Expired')

class Monitor(ProxyHelper):
    """ Upload console log if present to Scheduler
         and look for panic/bug/etc..
    """

    def __init__(self, watchdog, logger, conf, *args, **kwargs):
        """ Monitor system
        """
        self.log = logger
        self.conf = conf
        self.watchdog = watchdog
        self.logger.debug("Initialize monitor for system: %s" % self.watchdog['system'])
        self.watchedFiles = [WatchFile("%s/%s" % (self.conf["CONSOLE_LOGS"], self.watchdog["system"]),self.watchdog,self, self.conf["PANIC_REGEX"])]

    def run(self):
        """ check the logs for new data to upload/or cp
        """
        # watch the console log
        updated = False
        logs = filter(os.path.isfile, glob.glob('%s/%s/*' % ( self.conf["ANAMON_LOGS"], self.watchdog["system"])))
        for log in logs:
            if log not in self.watchedFiles:
                self.watchedFiles.append(WatchFile(log, self.watchdog,self, self.conf["PANIC_REGEX"]))
        for watchedFile in self.watchedFiles:
            if watchedFile.update():
                updated = True
        return updated

        
class Proxy(ProxyHelper):
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
        self.logger.info("task_upload_file task_id:%s name:%s offset:%s size:%s" % (task_id,
                                                                                    name,
                                                                                    offset,
                                                                                    size))
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
        self.logger.info("task_start %s" % task_id)
        return self.hub.recipes.tasks.start(task_id, kill_time)


    def install_start(self, system_name=None):
        """ Called from %pre of the test machine.  We record a start
        result on the scheduler and extend the watchdog
        This is a little ugly.. but better than putting this logic in
        kickstart
        """
        self.logger.info("install_start")
        # extend watchdog by 3 hours 60 * 60 * 3
        kill_time = 10800
        # look up system recipe based on hostname...
        # get first task
        recipeset = xmltramp.parse(self.get_recipe(system_name)).recipeSet
        try:
            task = recipeset.recipe.task()
        except AttributeError:
            task = recipeset.guestrecipe.task()
        # Only do this if first task is Running
        if task['status'] == 'Running':
            self.logger.info("Extending watchdog for task %s" % task['id'])
            self.hub.recipes.tasks.extend(task['id'], kill_time)
            self.logger.info("Recording /start for task %s" % task['id'])
            self.hub.recipes.tasks.result(task['id'],
                                          'pass_',
                                          '/start',
                                          0,
                                          'Install Started')
            return True
        return False

    def status_watchdog(self, task_id):
        """ Ask the scheduler how many seconds are left on a watchdog for this task
        """
        self.logger.info("status_watchdog %s %s", task_id)
        return self.hub.recipes.tasks.watchdog(task_id)

    def task_stop(self,
                  task_id,
                  stop_type,
                  msg=None):
        """ tell the scheduler that we are stoping a task
            stop_type = ['stop', 'abort', 'cancel']
            msg to record if issuing Abort or Cancel """
        self.logger.info("task_stop %s" % task_id)
        return self.hub.recipes.tasks.stop(task_id, stop_type, msg)

    def result_upload_file(self, 
                         result_id, 
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
        self.logger.info("result_upload_file result_id:%s name:%s offset:%s size:%s" % (result_id,
                                                                                        name,
                                                                                        offset,
                                                                                        size))
        return self.hub.recipes.tasks.result_upload_file(result_id, 
                                                  path, 
                                                  name, 
                                                  size, 
                                                  md5sum, 
                                                  offset, 
                                                  data)

    def push(self, fqdn, inventory):
        """ Push inventory data to Scheduler
        """
        return self.hub.push(fqdn, inventory)

    def legacypush(self, fqdn, inventory):
        """ Push legacy inventory data to Scheduler
        """
        return self.hub.legacypush(fqdn, inventory)
