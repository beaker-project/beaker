
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import errno
import os
import sys
import logging
import time
import base64
import lxml.etree
import re
import json
import shutil
import tempfile
import xmlrpclib
import subprocess
import pkg_resources
import shlex
from xml.sax.saxutils import escape as xml_escape, quoteattr as xml_quoteattr
from werkzeug.wrappers import Response
from werkzeug.exceptions import BadRequest, NotAcceptable, NotFound, \
        LengthRequired, UnsupportedMediaType, Conflict
from werkzeug.utils import redirect
from werkzeug.http import parse_content_range_header
from werkzeug.wsgi import wrap_file
from bkr.common.hub import HubProxy
from bkr.labcontroller.config import get_conf
from bkr.labcontroller.log_storage import LogStorage
import utils
try:
    #pylint: disable=E0611
    from subprocess import check_output
except ImportError:
    from utils import check_output

logger = logging.getLogger(__name__)

def replace_with_blanks(match):
    return ' ' * (match.end() - match.start() - 1) + '\n'


class ProxyHelper(object):


    def __init__(self, conf=None, hub=None, **kwargs):
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
        self.hub = hub
        if self.hub is None:
            self.hub = HubProxy(logger=logging.getLogger('bkr.common.hub.HubProxy'), conf=self.conf,
                    **kwargs)
        self.log_storage = LogStorage(self.conf.get("CACHEPATH"),
                "%s://%s/beaker/logs" % (self.conf.get('URL_SCHEME',
                'http'), self.conf.get_url_domain()),
                self.hub)

    def close(self):
        if sys.version_info >= (2, 7):
            self.hub._hub('close')()

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
        """
        # Originally offset=-1 had special meaning, but that was unused
        logger.debug("recipe_upload_file recipe_id:%s name:%s offset:%s size:%s",
                recipe_id, name, offset, size)
        with self.log_storage.recipe(str(recipe_id), os.path.join(path, name)) as log_file:
            log_file.update_chunk(base64.decodestring(data), int(offset or 0))
        return True

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

    def get_peer_roles(self, task_id):
        logger.debug('get_peer_roles %s', task_id)
        return self.hub.recipes.tasks.peer_roles(task_id)

    def extend_watchdog(self, task_id, kill_time):
        """ tell the scheduler to extend the watchdog by kill_time seconds
        """
        logger.debug("extend_watchdog %s %s", task_id, kill_time)
        return self.hub.recipes.tasks.extend(task_id, kill_time)

    def task_to_dict(self, task_name):
        """ returns metadata about task_name from the TaskLibrary
        """
        return self.hub.tasks.to_dict(task_name)

    def get_console_log(self, recipe_id, length=None):
        """
        Get console log from the OpenStack instance
        """
        return self.hub.recipes.console_output(recipe_id, length)

class ConsoleLogHelper(object):
    """
    Helper class to watch console log outputs and upload them to Scheduler
    """
    blocksize = 65536

    def __init__(self, watchdog, proxy, panic, logfile_name=None):
        self.watchdog = watchdog
        self.proxy = proxy
        self.logfile_name = logfile_name if logfile_name is not None else "console.log"
        self.strip_ansi = re.compile("(\033\[[0-9;\?]*[ABCDHfsnuJKmhr])")
        ascii_control_chars = map(chr, range(0, 32) + [127])
        keep_chars = '\t\n'
        strip_control_chars = [c for c in ascii_control_chars if c not in keep_chars]
        self.strip_cntrl = re.compile('[%s]' % re.escape(''.join(strip_control_chars)))
        self.panic_detector = PanicDetector(panic)
        self.install_failure_detector = InstallFailureDetector()
        self.where = 0
        self.incomplete_line = ''

    def process_log(self, block):
        # Sanitize control characters
        # We can't just strip the ansi codes, that would change the size
        # of the file, so whatever we end up stripping needs to be replaced
        # with spaces and a terminating \n.
        if self.strip_ansi:
            block = self.strip_ansi.sub(replace_with_blanks, block)
        if self.strip_cntrl:
            block = self.strip_cntrl.sub(' ', block)
        # Check for panics
        # Only feed the panic detector complete lines. If we have read a part
        # of a line, store it in self.incomplete_line and it will be prepended
        # to the subsequent block.
        lines = (self.incomplete_line + block).split('\n')
        self.incomplete_line = lines.pop()
        # Guard against a pathological case of the console filling up with
        # bytes but no newlines. Avoid buffering them into memory forever.
        if len(self.incomplete_line) > self.blocksize * 2:
            lines.append(self.incomplete_line)
            self.incomplete_line = ''
        if self.panic_detector:
            for line in lines:
                panic_found = self.panic_detector.feed(line)
                if panic_found:
                    self.proxy.report_panic(self.watchdog, panic_found)
                failure_found = self.install_failure_detector.feed(line)
                if failure_found:
                    self.proxy.report_install_failure(self.watchdog, failure_found)
        # Store block
        try:
            log_file = self.proxy.log_storage.recipe(
                    str(self.watchdog['recipe_id']),
                    self.logfile_name, create=(self.where == 0))
            with log_file:
                log_file.update_chunk(block, self.where)
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                pass # someone has removed our log, discard the update
            else:
                raise


class ConsoleWatchLogFiles(object):
    """ Monitor a directory for log files and upload them """
    def __init__(self, logdir, system_name, watchdog, proxy, panic):
        self.logdir = os.path.abspath(logdir)
        self.system_name = system_name
        self.watchdog = watchdog
        self.proxy = proxy
        self.panic = panic

        self.logfiles = {}
        for filename, logfile_name in utils.get_console_files(
                console_logs_directory=self.logdir, system_name=self.system_name):
            logger.info('Watching console log file %s for recipe %s',
                        filename, self.watchdog['recipe_id'])
            self.logfiles[filename] = ConsoleWatchFile(
                log=filename, watchdog=self.watchdog, proxy=self.proxy,
                panic=self.panic, logfile_name=logfile_name)

    def update(self):
        # Check for any new log files
        for filename, logfile_name in utils.get_console_files(
                console_logs_directory=self.logdir, system_name=self.system_name):
            if filename not in self.logfiles:
                logger.info('Watching console log file %s for recipe %s',
                            filename, self.watchdog['recipe_id'])
                self.logfiles[filename] = ConsoleWatchFile(
                    log=filename, watchdog=self.watchdog, proxy=self.proxy,
                    panic=self.panic, logfile_name=logfile_name)

        # Update all of our log files. If any had updated data return True
        updated = False
        for console_log in self.logfiles.values():
            updated |= console_log.update()
        return updated


class ConsoleWatchFile(ConsoleLogHelper):

    def __init__(self, log, watchdog, proxy, panic, logfile_name=None):
        self.log = log
        super(ConsoleWatchFile, self).__init__(
            watchdog, proxy, panic, logfile_name=logfile_name)

    def update(self):
        """
        If the log exists and the file has grown then upload the new piece
        """
        try:
            file = open(self.log, "r")
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                return False # doesn't exist
            else:
                raise
        try:
            file.seek(self.where)
            block = file.read(self.blocksize)
            now = file.tell()
        finally:
            file.close()
        if not block:
            return False # nothing new has been read
        self.process_log(block)
        self.where = now
        return True

    def truncate(self):
        try:
            f = open(self.log, 'r+')
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
        else:
            f.truncate()
        self.where = 0


class ConsoleWatchVirt(ConsoleLogHelper):
    """
    Watch console logs from virtual machines
    """
    def update(self):
        output = self.proxy.get_console_log(self.watchdog['recipe_id'])
        # OpenStack returns the console output as unicode, although it just
        # replaces all non-ASCII bytes with U+FFFD REPLACEMENT CHARACTER.
        # But Beaker normally deals in raw bytes for the consoles.
        # We can't get back the original bytes that OpenStack discarded so
        # let's just convert to UTF-8 so that the U+FFFD characters are written
        # properly at least.
        output = output.encode('utf8')
        if len(output) >= 102400:
            # If the console log is more than 100KB OpenStack only returns the *last* 100KB.
            # https://bugs.launchpad.net/nova/+bug/1081436
            # So we have to treat this chunk as if it were the entire file contents,
            # since we don't know the actual byte position anymore.
            block = output
            now = len(block)
            self.where = 0
        else:
            block = output[self.where:]
            now = self.where + len(block)
            if not block:
                return False
        self.process_log(block)
        self.where = now
        return True


class PanicDetector(object):

    def __init__(self, pattern):
        self.pattern = re.compile(pattern)
        self.fired = False

    def feed(self, line):
        if self.fired:
            return
        # Search the line for panics
        # The regex is stored in /etc/beaker/proxy.conf
        match = self.pattern.search(line)
        if match:
            self.fired = True
            return match.group()

class InstallFailureDetector(object):

    def __init__(self):
        self.patterns = []
        for raw_pattern in self._load_patterns():
            pattern = re.compile(raw_pattern)
            # If the pattern is empty, it is either a mistake or the admin is
            # trying to override a package pattern to disable it. Either way,
            # exclude it from the list.
            if pattern.search(''):
                continue
            self.patterns.append(pattern)
        self.fired = False

    def _load_patterns(self):
        site_dir = '/etc/beaker/install-failure-patterns'
        try:
            site_patterns = os.listdir(site_dir)
        except OSError, e:
            if e.errno == errno.ENOENT:
                site_patterns = []
            else:
                raise
        package_patterns = pkg_resources.resource_listdir('bkr.labcontroller',
                'install-failure-patterns')
        # site patterns override package patterns of the same name
        for p in site_patterns:
            if p in package_patterns:
                package_patterns.remove(p)
        patterns = []
        for p in site_patterns:
            try:
                patterns.append(open(os.path.join(site_dir, p), 'r').read().strip())
            except OSError, e:
                if e.errno == errno.ENOENT:
                    pass # readdir race
                else:
                    raise
        for p in package_patterns:
            patterns.append(pkg_resources.resource_string('bkr.labcontroller',
                    'install-failure-patterns/' + p))
        return patterns

    def feed(self, line):
        if self.fired:
            return
        for pattern in self.patterns:
            match = pattern.search(line)
            if match:
                self.fired = True
                return match.group()


class LogArchiver(ProxyHelper):

    def transfer_logs(self):
        transfered = False
        server = self.conf.get_url_domain()
        logger.debug('Polling for recipes to be transferred')
        try:
            recipe_ids = self.hub.recipes.by_log_server(server)
        except xmlrpclib.Fault as fault:
            if 'Anonymous access denied' in fault.faultString:
                logger.debug('Session expired, re-authenticating')
                self.hub._login()
                recipe_ids = self.hub.recipes.by_log_server(server)
            else:
                raise
        for recipe_id in recipe_ids:
            transfered = True
            self.transfer_recipe_logs(recipe_id)
        return transfered

    def transfer_recipe_logs(self, recipe_id):
        """ If Cache is turned on then move the recipes logs to their final place
        """
        tmpdir = tempfile.mkdtemp(dir=self.conf.get("CACHEPATH"))
        try:
            # Move logs to tmp directory layout
            logger.debug('Fetching files list for recipe %s', recipe_id)
            mylogs = self.hub.recipes.files(recipe_id)
            trlogs = []
            logger.debug('Building temporary log tree for transfer under %s', tmpdir)
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
                        logger.exception('Error hard-linking %s to %s', mysrc, mydst)
                        return
                else:
                    logger.warn('Recipe %s file %s missing on disk, ignoring',
                            recipe_id, mysrc)
            # rsync the logs to their new home
            rsync_succeeded  = self.rsync('%s/' % tmpdir, '%s' % self.conf.get("ARCHIVE_RSYNC"))
            if not rsync_succeeded:
                return
            # if the logs have been transferred then tell the server the new location
            logger.debug('Updating recipe %s file locations on the server', recipe_id)
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
        args = ['rsync'] + shlex.split(self.conf.get('RSYNC_FLAGS', '')) + [src, dst]
        logger.debug('Invoking rsync as %r', args)
        p = subprocess.Popen(args, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            logger.error('Failed to rsync recipe logs from %s to %s\nExit status: %s\n%s',
                    src, dst, p.returncode, err)
            return False
        return True

    def sleep(self):
        # Sleep between polling
        time.sleep(self.conf.get("SLEEP_TIME", 20))

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
        self.log_storage = obj.log_storage
        if(self.watchdog['is_virt_recipe']):
            logger.info('Watching OpenStack console for recipe %s', self.watchdog['recipe_id'])
            self.console_watch = ConsoleWatchVirt(
                    self.watchdog, self, self.conf["PANIC_REGEX"])
        else:
            self.console_watch = ConsoleWatchLogFiles(
                logdir=self.conf['CONSOLE_LOGS'],
                system_name=self.watchdog['system'], watchdog=self.watchdog,
                proxy=self, panic=self.conf["PANIC_REGEX"])

    def run(self):
        """ check the logs for new data to upload/or cp
        """
        return self.console_watch.update()

    def report_panic(self, watchdog, panic_message):
        logger.info('Panic detected for recipe %s on system %s: '
                'console log contains string %r', watchdog['recipe_id'],
                watchdog['system'], panic_message)
        job = lxml.etree.fromstring(self.get_my_recipe(
                dict(recipe_id=watchdog['recipe_id'])))
        recipe = job.find('recipeSet/guestrecipe')
        if recipe is None:
            recipe = job.find('recipeSet/recipe')
        if recipe.find('watchdog').get('panic') == 'ignore':
            # Don't Report the panic
            logger.info('Not reporting panic due to panic=ignore')
        elif recipe.get('status') == 'Reserved':
            logger.info('Not reporting panic as recipe is reserved')
        else:
            # Report the panic
            # Look for active task, worst case it records it on the last task
            for task in recipe.iterfind('task'):
                if task.get('status') == 'Running':
                    break
            self.task_result(task.get('id'), 'panic', '/', 0, panic_message)
            # set the watchdog timeout to 10 minutes, gives some time for all data to
            # print out on the serial console
            # this may abort the recipe depending on what the recipeSets
            # watchdog behaviour is set to.
            self.extend_watchdog(task.get('id'), 60 * 10)

    def report_install_failure(self, watchdog, failure_message):
        logger.info('Install failure detected for recipe %s on system %s: '
                'console log contains string %r', watchdog['recipe_id'],
                watchdog['system'], failure_message)
        job = lxml.etree.fromstring(self.get_my_recipe(
                dict(recipe_id=watchdog['recipe_id'])))
        recipe = job.find('recipeSet/guestrecipe')
        if recipe is None:
            recipe = job.find('recipeSet/recipe')
        # For now we are re-using the same panic="" attribute which is used to
        # control panic detection, bug 1055320 is an RFE to change this
        if recipe.find('watchdog').get('panic') == 'ignore':
            logger.info('Not reporting install failure due to panic=ignore')
        elif recipe.find('installation') is not None and recipe.find('installation').get('install_finished'):
            logger.info('Not reporting install failure for finished installation')
        else:
            # Ideally we would record it against the Installation entity for
            # the recipe, but that's not a thing yet, so we just add a result
            # to the first task (which is typically /distribution/install)
            first_task = recipe.findall('task')[0]
            self.task_result(first_task.get('id'), 'fail', '/', 0, failure_message)
            self.recipe_stop(recipe.get('id'), 'abort', 'Installation failed')

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
        """
        # Originally offset=-1 had special meaning, but that was unused
        logger.debug("task_upload_file task_id:%s name:%s offset:%s size:%s",
                task_id, name, offset, size)
        with self.log_storage.task(str(task_id), os.path.join(path, name)) as log_file:
            log_file.update_chunk(base64.decodestring(data), int(offset or 0))
        return True

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
        p = subprocess.Popen(["sudo", "/usr/bin/beaker-clear-netboot", fqdn],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, _ = p.communicate()
        if p.returncode:
            raise RuntimeError('sudo beaker-clear-netboot failed: %s' % output.strip())
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

    def install_fail(self, recipe_id=None):
        _debug_id = "(unspecified recipe)" if recipe_id is None else recipe_id
        logger.debug("install_fail for R:%s", _debug_id)
        return self.hub.recipes.install_fail(recipe_id)

    def postinstall_done(self, recipe_id=None):
        logger.debug("postinstall_done recipe_id=%s", recipe_id)
        return self.hub.recipes.postinstall_done(recipe_id)

    def status_watchdog(self, task_id):
        """ Ask the scheduler how many seconds are left on a watchdog for this task
        """
        logger.debug("status_watchdog %s", task_id)
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
        """
        # Originally offset=-1 had special meaning, but that was unused
        logger.debug("result_upload_file result_id:%s name:%s offset:%s size:%s",
                result_id, name, offset, size)
        with self.log_storage.result(str(result_id), os.path.join(path, name)) as log_file:
            log_file.update_chunk(base64.decodestring(data), int(offset or 0))
        return True

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
        return self.hub.labcontrollers.get_installation_for_system(fqdn)

class ProxyHTTP(object):

    def __init__(self, proxy):
        self.hub = proxy.hub
        self.log_storage = proxy.log_storage

    def get_recipe(self, req, recipe_id):
        if req.accept_mimetypes.provided and \
                'application/xml' not in req.accept_mimetypes:
            raise NotAcceptable()
        return Response(self.hub.recipes.to_xml(recipe_id),
                content_type='application/xml')

    _result_types = { # maps from public API names to internal Beaker names
        'pass': 'pass_',
        'warn': 'warn',
        'fail': 'fail',
        'none': 'result_none',
        'skip': 'skip',
    }
    def post_result(self, req, recipe_id, task_id):
        if 'result' not in req.form:
            raise BadRequest('Missing "result" parameter')
        result = req.form['result'].lower()
        if result not in self._result_types:
            raise BadRequest('Unknown result type %r' % req.form['result'])
        try:
            result_id = self.hub.recipes.tasks.result(task_id,
                    self._result_types[result],
                    req.form.get('path'), req.form.get('score'),
                    req.form.get('message'))
        except xmlrpclib.Fault, fault:
            # XXX need to find a less fragile way to do this
            if 'Cannot record result for finished task' in fault.faultString:
                return Response(status=409, response=fault.faultString,
                        content_type='text/plain')
            elif 'Too many results in recipe' in fault.faultString:
                return Response(status=403, response=fault.faultString,
                        content_type='text/plain')
            else:
                raise
        return redirect('/recipes/%s/tasks/%s/results/%s' % (
                recipe_id, task_id, result_id), code=201)

    def post_recipe_status(self, req, recipe_id):
        if 'status' not in req.form:
            raise BadRequest('Missing "status" parameter')
        status = req.form['status'].lower()
        if status != 'aborted':
            raise BadRequest('Unknown status %r' % req.form['status'])
        self.hub.recipes.stop(recipe_id, 'abort',
                req.form.get('message'))
        return Response(status=204)

    def post_task_status(self, req, recipe_id, task_id):
        if 'status' not in req.form:
            raise BadRequest('Missing "status" parameter')
        self._update_status(task_id, req.form['status'], req.form.get('message'))
        return Response(status=204)

    def _update_status(self, task_id, status, message):
        status = status.lower()
        if status not in ['running', 'completed', 'aborted']:
            raise BadRequest('Unknown status %r' % status)
        try:
            if status == 'running':
                self.hub.recipes.tasks.start(task_id)
            elif status == 'completed':
                self.hub.recipes.tasks.stop(task_id, 'stop')
            elif status == 'aborted':
                self.hub.recipes.tasks.stop(task_id, 'abort', message)
        except xmlrpclib.Fault as fault:
            # XXX This has to be completely replaced with JSON response in next major release
            # We don't want to blindly return 500 because of opposite side
            # will try to retry request - which is almost in all situation wrong
            if ('Cannot restart finished task' in fault.faultString
                    or 'Cannot change status for finished task' in fault.faultString):
                raise Conflict(fault.faultString)
            else:
                raise

    def patch_task(self, request, recipe_id, task_id):
        if request.json:
            data = dict(request.json)
        elif request.form:
            data = request.form.to_dict()
        else:
            raise UnsupportedMediaType
        if 'status' in data:
            status = data.pop('status')
            self._update_status(task_id, status, data.pop('message', None))
            # If the caller only wanted to update the status and nothing else,
            # we will avoid making a second XML-RPC call.
            updated = {'status': status}
        if data:
            updated = self.hub.recipes.tasks.update(task_id, data)
        return Response(status=200, response=json.dumps(updated),
                content_type='application/json')

    def get_watchdog(self, req, recipe_id):
        seconds = self.hub.recipes.watchdog(recipe_id)
        return Response(status=200,
                response=json.dumps({'seconds': seconds}),
                content_type='application/json')

    def post_watchdog(self, req, recipe_id):
        if 'seconds' not in req.form:
            raise BadRequest('Missing "seconds" parameter')
        try:
            seconds = int(req.form['seconds'])
        except ValueError:
            raise BadRequest('Invalid "seconds" parameter %r' % req.form['seconds'])
        self.hub.recipes.extend(recipe_id, seconds)
        return Response(status=204)

    # XXX should do streaming here, so that clients can send
    # big files without chunking

    def _put_log(self, log_file, req):
        if req.content_length is None:
            raise LengthRequired()
        content_range = parse_content_range_header(req.headers.get('Content-Range'))
        if content_range:
            # a few sanity checks
            if req.content_length != (content_range.stop - content_range.start):
                raise BadRequest('Content length does not match range length')
            if content_range.length and content_range.length < content_range.stop:
                raise BadRequest('Total length is smaller than range end')
        try:
            with log_file:
                if content_range:
                    if content_range.length: # length may be '*' meaning unspecified
                        log_file.truncate(content_range.length)
                    log_file.update_chunk(req.data, content_range.start)
                else:
                    # no Content-Range, therefore the request is the whole file
                    log_file.truncate(req.content_length)
                    log_file.update_chunk(req.data, 0)
        # XXX need to find a less fragile way to do this
        except xmlrpclib.Fault, fault:
            if 'Cannot register file for finished ' in fault.faultString:
                return Response(status=409, response=fault.faultString,
                        content_type='text/plain')
            elif 'Too many ' in fault.faultString:
                return Response(status=403, response=fault.faultString,
                        content_type='text/plain')
            else:
                raise
        return Response(status=204)

    def _get_log(self, log_file, req):
        try:
            f = log_file.open_ro()
        except IOError, e:
            if e.errno == errno.ENOENT:
                raise NotFound()
            else:
                raise
        return Response(status=200, response=wrap_file(req.environ, f),
                content_type='text/plain', direct_passthrough=True)

    def do_recipe_log(self, req, recipe_id, path):
        log_file = self.log_storage.recipe(recipe_id, path)
        if req.method == 'GET':
            return self._get_log(log_file, req)
        elif req.method == 'PUT':
            return self._put_log(log_file, req)

    def do_task_log(self, req, recipe_id, task_id, path):
        log_file = self.log_storage.task(task_id, path)
        if req.method == 'GET':
            return self._get_log(log_file, req)
        elif req.method == 'PUT':
            return self._put_log(log_file, req)

    def do_result_log(self, req, recipe_id, task_id, result_id, path):
        log_file = self.log_storage.result(result_id, path)
        if req.method == 'GET':
            return self._get_log(log_file, req)
        elif req.method == 'PUT':
            return self._put_log(log_file, req)

    # XXX use real templates here, make the Atom feed valid

    def _html_log_index(self, logs):
        hrefs = [os.path.join((log['path'] or '').lstrip('/'), log['filename'])
                for log in logs]
        lis = ['<li><a href=%s>%s</a></li>' % (xml_quoteattr(href), xml_escape(href))
                for href in hrefs]
        html = '<!DOCTYPE html><html><body><ul>%s</ul></body></html>' % ''.join(lis)
        return Response(status=200, content_type='text/html', response=html)

    def _atom_log_index(self, logs):
        hrefs = [os.path.join((log['path'] or '').lstrip('/'), log['filename'])
                for log in logs]
        entries = ['<entry><link rel="alternate" href=%s /><title type="text">%s</title></entry>'
                % (xml_quoteattr(href), xml_escape(href)) for href in hrefs]
        atom = '<feed xmlns="http://www.w3.org/2005/Atom">%s</feed>' % ''.join(entries)
        return Response(status=200, content_type='application/atom+xml', response=atom)

    def _log_index(self, req, logs):
        if not req.accept_mimetypes.provided:
            response_type = 'text/html'
        else:
            response_type = req.accept_mimetypes.best_match(['text/html', 'application/atom+xml'])
            if not response_type:
                raise NotAcceptable()
        if response_type == 'text/html':
            return self._html_log_index(logs)
        elif response_type == 'application/atom+xml':
            return self._atom_log_index(logs)

    def list_recipe_logs(self, req, recipe_id):
        try:
            logs = self.hub.taskactions.files('R:%s' % recipe_id)
        except xmlrpclib.Fault, fault:
            # XXX need to find a less fragile way to do this
            if 'is not a valid Recipe id' in fault.faultString:
                raise NotFound()
            else:
                raise
        # The server includes all sub-elements' logs, filter them out
        logs = [log for log in logs if log['tid'].startswith('R:')]
        return self._log_index(req, logs)

    def list_task_logs(self, req, recipe_id, task_id):
        try:
            logs = self.hub.taskactions.files('T:%s' % task_id)
        except xmlrpclib.Fault, fault:
            # XXX need to find a less fragile way to do this
            if 'is not a valid RecipeTask id' in fault.faultString:
                raise NotFound()
            else:
                raise
        # The server includes all sub-elements' logs, filter them out
        logs = [log for log in logs if log['tid'].startswith('T:')]
        return self._log_index(req, logs)

    def list_result_logs(self, req, recipe_id, task_id, result_id):
        try:
            logs = self.hub.taskactions.files('TR:%s' % result_id)
        except xmlrpclib.Fault, fault:
            # XXX need to find a less fragile way to do this
            if 'is not a valid RecipeTaskResult id' in fault.faultString:
                raise NotFound()
            else:
                raise
        return self._log_index(req, logs)

    def put_power(self, req, fqdn):
        """
        Controls power for the system with the given fully-qualified domain
        name.

        :param req: request
        :param fqdn: fully-qualified domain name of the system to be power controlled
        """
        if req.json:
            payload = dict(req.json)
        elif req.form:
            payload = req.form.to_dict()
        else:
            raise UnsupportedMediaType

        if 'action' not in payload:
            raise BadRequest('Missing "action" parameter')
        action = payload['action']
        if action not in ['on', 'off', 'reboot']:
            raise BadRequest('Unknown action {}'.format(action))

        self.hub.systems.power(action, fqdn, False, True)
        return Response(status=204)

    def healthz(self, req):
        """
        Health check

        :param req: request
        """
        # HEAD is identical to GET except that it MUST NOT return a body in the response
        response = "We are healthy!" if req.method == 'GET' else None

        return Response(status=200, response=response)
