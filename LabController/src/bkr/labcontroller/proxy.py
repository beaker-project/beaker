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
import shutil
import tempfile
import xmlrpclib
import subprocess
from cStringIO import StringIO
from socket import gethostname
from threading import Thread, Event
from werkzeug.wrappers import Response
from werkzeug.exceptions import BadRequest, NotAcceptable
from werkzeug.utils import redirect
import kobo.conf
from kobo.client import HubProxy
from kobo.exceptions import ShutdownException
from kobo.xmlrpc import retry_request_decorator, CookieTransport, \
        SafeCookieTransport
from bkr.labcontroller.config import get_conf
from kobo.process import kill_process_group
from bkr.upload import Uploader
import utils
try:
    from subprocess import check_output
except ImportError:
    from utils import check_output

try:
    from hashlib import md5 as md5_constructor
except ImportError:
    from md5 import new as md5_constructor

logger = logging.getLogger(__name__)

def replace_with_blanks(match):
    return ' ' * (match.end() - match.start() - 1) + '\n'

class ProxyHelper(object):


    def __init__(self, conf=None, **kwargs):
        self.conf = get_conf()

        # update data from another config
        if conf is not None:
            self.conf.load_from_conf(conf)

        # update data from config specified in os.environ
        conf_environ_key = "BEAKER_PROXY_CONFIG_FILE"
        if conf_environ_key in os.environ:
            self.conf.load_from_file(os.environ[conf_environ_key])

        self.conf.load_from_dict(kwargs)

        # self.hub is created here
        if self.conf['HUB_URL'].startswith('https://'):
            TransportClass = retry_request_decorator(SafeCookieTransport)
        else:
            TransportClass = retry_request_decorator(CookieTransport)
        self.hub = HubProxy(logger=logging.getLogger('kobo.client.HubProxy'), conf=self.conf,
                transport=TransportClass(timeout=120), auto_logout=False, **kwargs)
        self.log_base_url = "http://%s/beaker/logs" % self.conf.get("SERVER", gethostname())
        self.basepath = self.conf.get("CACHEPATH", "/var/www/beaker/logs")
        self.upload = Uploader('%s' % self.basepath).uploadFile

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
        logger.debug("recipe_upload_file recipe_id:%s name:%s offset:%s size:%s",
                recipe_id, name, offset, size)
        if int(offset) == 0:
            self.hub.recipes.register_file(
                    '%s/recipes/%s/' % (self.log_base_url, recipe_id),
                    recipe_id, path, name,
                    '%s/recipes/%s/' % (self.basepath, recipe_id))
        return self.upload('/recipes/%s/%s' % (recipe_id, path),
                name, size, md5sum, offset, data)

    def task_result(self, 
                    task_id, 
                    result_type, 
                    result_path=None, 
                    result_score=None,
                    result_summary=None):
        """ report a result to the scheduler """
        logger.debug("task_result %s", task_id)
        return self.hub.recipes.tasks.result(task_id,
                                             result_type,
                                             result_path,
                                             result_score,
                                             result_summary)

    def task_info(self,
                  qtask_id):
        """ accepts qualified task_id J:213 RS:1234 R:312 T:1234 etc.. Returns dict with status """
        logger.debug("task_info %s", qtask_id)
        return self.hub.taskactions.task_info(qtask_id)

    def recipe_stop(self,
                    recipe_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this recipe
            stop_type = ['abort', 'cancel']
            msg to record
        """
        logger.debug("recipe_stop %s", recipe_id)
        return self.hub.recipes.stop(recipe_id, stop_type, msg)

    def recipeset_stop(self,
                    recipeset_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this recipeset
            stop_type = ['abort', 'cancel']
            msg to record
        """
        logger.debug("recipeset_stop %s", recipeset_id)
        return self.hub.recipesets.stop(recipeset_id, stop_type, msg)

    def job_stop(self,
                    job_id,
                    stop_type,
                    msg=None):
        """ tell the scheduler that we are stopping this job
            stop_type = ['abort', 'cancel']
            msg to record 
        """
        logger.debug("job_stop %s", job_id)
        return self.hub.jobs.stop(job_id, stop_type, msg)

    def get_my_recipe(self, request):
        """
        Accepts a dict with key 'recipe_id'. Returns an XML document for the 
        recipe with that id.
        """
        if 'recipe_id' in request:
            logger.debug("get_recipe recipe_id:%s", request['recipe_id'])
            return self.hub.recipes.to_xml(request['recipe_id'])

    def extend_watchdog(self, task_id, kill_time):
        """ tell the scheduler to extend the watchdog by kill_time seconds
        """
        logger.debug("extend_watchdog %s %s", task_id, kill_time)
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
            self.strip_ansi = re.compile("(\033\[[0-9;\?]*[ABCDHfsnuJKmhr])")
            self.strip_cntrl = re.compile('[%s]' % re.escape(self.control_chars))
            self.panic = re.compile(r'%s' % panic)
        else:
            self.strip_ansi = None
            self.strip_cntrl = None
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
            # We can't just strip the ansi codes, that would change the size
            # of the file, so whatever we end up stripping needs to be replaced
            # with spaces and a terminating \n.
            if self.strip_ansi:
                line = self.strip_ansi.sub(replace_with_blanks, line)
            if self.strip_cntrl:
                line = self.strip_cntrl.sub(' ', line)
            now = file.tell()
            file.close()
            if self.panic:
                # Search the line for panics
                # The regex is stored in /etc/beaker/proxy.conf
                panic = self.panic.search(line)
                if panic:
                    logger.info("Panic detected for recipe %s, system %s",
                            self.watchdog['recipe_id'], self.watchdog['system'])
                    recipeset = xmltramp.parse(self.proxy.get_my_recipe(
                            dict(recipe_id=self.watchdog['recipe_id']))).recipeSet
                    try:
                        recipe = recipeset.recipe
                    except AttributeError:
                        recipe = recipeset.guestrecipe
                    watchdog = recipe.watchdog()
                    if 'panic' in watchdog and watchdog['panic'] == 'ignore':
                        # Don't Report the panic
                        logger.info("Not reporting panic, recipe set to ignore")
                    else:
                        # Report the panic
                        # Look for active task, worst case it records it on the last task
                        for task in recipe['task':]:
                            if task()['status'] == 'Running':
                                break
                        self.proxy.task_result(task()['id'], 'panic', '/', 0, panic.group())
                        # set the watchdog timeout to 10 minutes, gives some time for all data to 
                        # print out on the serial console
                        # this may abort the recipe depending on what the recipeSets
                        # watchdog behaviour is set to.
                        self.proxy.extend_watchdog(task()['id'], 60 * 10)
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
        return False

    def truncate(self):
        try:
            f = open(self.log, 'r+')
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
        else:
            f.truncate()
        self.where = 0


class Watchdog(ProxyHelper):

    watchdogs = dict()

    def transfer_logs(self):
        logger.info("Entering transfer_logs")
        transfered = False
        server = self.conf.get("SERVER", gethostname())
        for recipe_id in self.hub.recipes.by_log_server(server):
            transfered = True
            self.transfer_recipe_logs(recipe_id)
        logger.info("Exiting transfer_logs")
        return transfered

    def transfer_recipe_logs(self, recipe_id):
        """ If Cache is turned on then move the recipes logs to their final place
        """
        tmpdir = tempfile.mkdtemp(dir=self.basepath)
        try:
            # Move logs to tmp directory layout
            mylogs = self.hub.recipes.files(recipe_id)
            trlogs = []
            for mylog in mylogs:
                mysrc = '%s/%s/%s' % (mylog['basepath'], mylog['path'], mylog['filename'])
                mydst = '%s/%s/%s/%s' % (tmpdir, mylog['filepath'], 
                                          mylog['path'], mylog['filename'])
                if os.path.exists(mysrc):
                    if not os.path.exists(os.path.dirname(mydst)):
                        os.makedirs(os.path.dirname(mydst))
                    try:
                        os.link(mysrc,mydst)
                        trlogs.append(mylog)
                    except OSError, e:
                        logger.error('unable to hardlink %s to %s, %s', mysrc, mydst, e)
                        return
                else:
                        logger.warn('file missing: %s', mysrc)
            # rsync the logs to their new home
            rc = self.rsync('%s/' % tmpdir, '%s' % self.conf.get("ARCHIVE_RSYNC"))
            logger.debug("rsync rc=%s", rc)
            if rc == 0:
                # if the logs have been transferred then tell the server the new location
                self.hub.recipes.change_files(recipe_id, self.conf.get("ARCHIVE_SERVER"),
                                                         self.conf.get("ARCHIVE_BASEPATH"))
                for mylog in trlogs:
                    mysrc = '%s/%s/%s' % (mylog['basepath'], mylog['path'], mylog['filename'])
                    self.rm(mysrc)
                    try:
                        self.removedirs('%s/%s' % (mylog['basepath'], mylog['path']))
                    except OSError:
                        # It's ok if it fails, dir may not be empty yet
                        pass
        finally:
            # get rid of our tmpdir.
            shutil.rmtree(tmpdir)

    def rm(self, src):
        """ remove src
        """
        if os.path.exists(src):
            return os.unlink(src)
        return True

    def removedirs(self, path):
        """ remove empty dirs
        """
        if os.path.exists(path):
            return os.removedirs(path)
        return True

    def rsync(self, src, dst):
        """ Run system rsync command to move files
        """
        my_cmd = 'rsync %s %s %s' % (self.conf.get('RSYNC_FLAGS',''), src, dst)
        return utils.subprocess_call(my_cmd,shell=True)

    def purge_old_watchdog(self, watchdog_systems):
        try:
            del self.watchdogs[watchdog_systems]
        except KeyError, e:
            logger.error('Trying to remove a watchdog that is already removed')

    def expire_watchdogs(self, watchdogs):
        """Clear out expired watchdog entries"""

        logger.info("Entering expire_watchdogs")
        for watchdog in watchdogs:
            try:
                self.abort(watchdog)
            except xmlrpclib.Fault:
                # Catch xmlrpc.Fault's here so we keep iterating the loop
                logger.exception('Failed to abort expired watchdog')

    def active_watchdogs(self, watchdogs, purge=True):
        """Monitor active watchdog entries"""

        logger.info("Entering active_watchdogs")
        active_watchdogs = []
        for watchdog in watchdogs:
            watchdog_key = '%s:%s' % (watchdog['system'], watchdog['recipe_id'])
            active_watchdogs.append(watchdog_key)
            if watchdog_key not in self.watchdogs:
                self.watchdogs[watchdog_key] = Monitor(watchdog, self)
        # Remove Monitor if watchdog does not exist.
        if purge is True:
            for watchdog_system in self.watchdogs.copy():
                if watchdog_system not in active_watchdogs:
                    self.purge_old_watchdog(watchdog_system)
                    logger.info("Removed Monitor for %s", watchdog_system)

    def run(self):
        updated = False
        for monitor in self.watchdogs.values():
            try:
                updated |= monitor.run()
            except (xmlrpclib.Fault, OSError):
                logger.exception('Failed to run monitor for %s', monitor.watchdog['system'])
        return bool(updated)

    def sleep(self):
        # Sleep between polling
        time.sleep(self.conf.get("SLEEP_TIME", 20))

    def abort(self, watchdog):
        """ Abort expired watchdog entry
        """
        logger.info("External Watchdog Expired for %s", watchdog['system'])
        if self.conf.get("WATCHDOG_SCRIPT"):
            recipexml = self.get_my_recipe(dict(recipe_id=watchdog['recipe_id']))
            recipeset = xmltramp.parse(recipexml).recipeSet
            try:
                recipe = recipeset.recipe
            except AttributeError:
                recipe = recipeset.guestrecipe
            for task in recipe['task':]:
                if task()['status'] == 'Running':
                    break
            task_id = task()['id']
            try:
                args = [self.conf.get('WATCHDOG_SCRIPT'),
                        str(watchdog['system']),
                        str(watchdog['recipe_id']), str(task_id),
                       ]
                output = check_output(args)
                logger.debug("Extending T:%s watchdog %d" % (task_id,
                                                             int(output)))
                self.extend_watchdog(task_id, int(output))
                return
            except Exception:
                logger.exception('Error in watchdog script: %r', args)

        self.recipe_stop(watchdog['recipe_id'],
                         'abort',
                         'External Watchdog Expired')

class Monitor(ProxyHelper):
    """ Upload console log if present to Scheduler
         and look for panic/bug/etc..
    """

    def __init__(self, watchdog, obj, *args, **kwargs):
        """ Monitor system
        """
        self.watchdog = watchdog
        self.conf = obj.conf
        self.hub = obj.hub
        self.upload = obj.upload
        self.basepath = obj.basepath
        self.log_base_url = obj.log_base_url
        logger.info("Initialize monitor for system: %s", self.watchdog['system'])
        self.console_watch = WatchFile(
                "%s/%s" % (self.conf["CONSOLE_LOGS"], self.watchdog["system"]),
                self.watchdog,self, self.conf["PANIC_REGEX"])

    def run(self):
        """ check the logs for new data to upload/or cp
        """
        return self.console_watch.update()

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
        logger.debug("task_upload_file task_id:%s name:%s offset:%s size:%s",
                task_id, name, offset, size)
        if int(offset) == 0:
            self.hub.recipes.tasks.register_file(
                    '%s/tasks/%s/' % (self.log_base_url, task_id),
                    task_id, path, name,
                    '%s/tasks/%s/' % (self.basepath, task_id))
        return self.upload('/tasks/%s/%s' % (task_id, path),
                name, size, md5sum, offset, data)

    def task_start(self,
                   task_id,
                   kill_time=None):
        """ tell the scheduler that we are starting a task
            default watchdog time can be overridden with kill_time seconds """
        logger.debug("task_start %s", task_id)
        return self.hub.recipes.tasks.start(task_id, kill_time)


    def install_start(self, recipe_id=None):
        """ Called from %pre of the test machine.  We call
        the server's install_start()
        """
        _debug_id = "(unspecified recipe)" if recipe_id is None else recipe_id
        logger.debug("install_start for R:%s" % _debug_id)
        return self.hub.recipes.install_start(recipe_id)

    def clear_netboot(self, fqdn):
        ''' Called from %post section to remove netboot entry '''
        logger.debug('clear_netboot %s', fqdn)
        subprocess.check_call(["sudo", "/usr/bin/beaker-clear-netboot", fqdn])
        logger.debug('clear_netboot %s completed', fqdn)
        return self.hub.labcontrollers.add_completed_command(fqdn, "clear_netboot")

    def postreboot(self, recipe_id):
        # XXX would be nice if we could limit this so that systems could only
        # reboot themselves, instead of accepting any arbitrary recipe id
        logger.debug('postreboot %s', recipe_id)
        return self.hub.recipes.postreboot(recipe_id)

    def power(self, hostname, action):
        # XXX this should also be authenticated and
        # restricted to systems in the same recipeset as the caller
        logger.debug('power %s %s', hostname, action)
        return self.hub.systems.power(action, hostname, False,
                # force=True because we are not the system's user
                True)

    def install_done(self, recipe_id=None, fqdn=None):
        logger.debug("install_done recipe_id=%s fqdn=%s", recipe_id, fqdn)
        return self.hub.recipes.install_done(recipe_id, fqdn)

    def postinstall_done(self, recipe_id=None):
        logger.debug("postinstall_done recipe_id=%s", recipe_id)
        return self.hub.recipes.postinstall_done(recipe_id)

    def status_watchdog(self, task_id):
        """ Ask the scheduler how many seconds are left on a watchdog for this task
        """
        logger.debug("status_watchdog %s %s", task_id)
        return self.hub.recipes.tasks.watchdog(task_id)

    def task_stop(self,
                  task_id,
                  stop_type,
                  msg=None):
        """ tell the scheduler that we are stoping a task
            stop_type = ['stop', 'abort', 'cancel']
            msg to record if issuing Abort or Cancel """
        logger.debug("task_stop %s", task_id)
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
        logger.debug("result_upload_file result_id:%s name:%s offset:%s size:%s",
                result_id, name, offset, size)
        if int(offset) == 0:
            self.hub.recipes.tasks.register_result_file(
                    '%s/results/%s/' % (self.log_base_url, result_id),
                    result_id, path, name,
                    '%s/results/%s/' % (self.basepath, result_id))
        return self.upload('/results/%s/%s' % (result_id, path),
                name, size, md5sum, offset, data)

    def push(self, fqdn, inventory):
        """ Push inventory data to Scheduler
        """
        return self.hub.push(fqdn, inventory)

    def legacypush(self, fqdn, inventory):
        """ Push legacy inventory data to Scheduler
        """
        return self.hub.legacypush(fqdn, inventory)

    def updateDistro(self, distro, arch):
        """ This proxy method allows the installed machine
            to report that the distro was successfully installed
            The Scheduler will add an INSTALLS tag to this
            distro/arch, and if all distro/arch combo's
            contain an INSTALLS tag then it will also add
            a STABLE tag signifying that it successfully installed
            on all applicable arches.
        """
        return self.hub.tags.updateDistro(distro, arch)

    def add_distro_tree(self, distro):
        """ This proxy method allows the lab controller to add new
            distros to the Scheduler/Inventory server.
        """
        return self.hub.labcontrollers.add_distro_tree(distro)

    def remove_distro_trees(self, distro_tree_ids):
        """ This proxy method allows the lab controller to remove
            distro_tree_ids from the Scheduler/Inventory server.
        """
        return self.hub.labcontrollers.remove_distro_trees(distro_tree_ids)

    def get_distro_trees(self, filter=None):
        """ This proxy method allows the lab controller to query
            for all distro_trees that are associated to it.
        """
        return self.hub.labcontrollers.get_distro_trees(filter)

    def get_installation_for_system(self, fqdn):
        """
        A system can call this to get the details of the distro tree which was
        most recently installed on it.
        """
        # TODO tie this in to installation tracking when that is implemented
        return self.hub.labcontrollers.get_last_netboot_for_system(fqdn)

class ProxyHTTP(object):

    def __init__(self, proxy):
        self.hub = proxy.hub
        self.log_storage = proxy.log_storage

    def get_recipe(self, req, recipe_id):
        if req.accept_mimetypes and 'application/xml' not in req.accept_mimetypes:
            raise NotAcceptable()
        return Response(self.hub.recipes.to_xml(recipe_id),
                content_type='application/xml')

    _result_types = { # maps from public API names to internal Beaker names
        'pass': 'pass_',
        'warn': 'warn',
        'fail': 'fail',
    }
    def post_result(self, req, recipe_id, task_id):
        if 'result' not in req.form:
            raise BadRequest('Missing "result" parameter')
        result = req.form['result'].lower()
        if result not in self._result_types:
            raise BadRequest('Unknown result type %r' % req.form['result'])
        result_id = self.hub.recipes.tasks.result(task_id,
                self._result_types[result],
                req.form.get('path'), req.form.get('score'),
                req.form.get('message'))
        return redirect('/recipes/%s/tasks/%s/results/%s' % (
                recipe_id, task_id, result_id), code=201)
