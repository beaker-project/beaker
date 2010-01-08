# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor

import sys
import os
import os.path
import traceback
import base64
import hashlib
import simplejson as json
import logging
from xml.dom import minidom

from beah.misc.log_this import log_this
from beah.misc import format_exc, dict_update, log_flush

from beah.core.backends import ExtBackend
from beah.core import command, event, addict
from beah.core.constants import ECHO, RC
from beah import config

import beah.system
# FIXME: using rpm's, yum - too much Fedora centric(?)
from beah.system.dist_fedora import RPMInstaller
from beah.system.os_linux import ShExecutable
from beah.wires.internals.twbackend import start_backend, log_handler

"""
Beaker Backend.

Beaker Backend should invoke these XML-RPC:
 1. recipes.to_xml(recipe_id)
    recipes.system_xml(fqdn)
 2. parse XML
 3. recipes.tasks.Start(task_id, kill_time)
 *. recipes.tasks.Result(task_id, result_type, path, score, summary)
    - result_type: pass_|warn|fail|panic
 4. recipes.tasks.Stop(task_id, stop_type, msg)
    - stop_type: stop|abort|cancel
"""

conf = config.config()

log_handler('beah_beaker_backend.log')
log = logging.getLogger('backend')

# FIXME: Use config option for log_on:
print_this = log_this(lambda s: log.debug(s), log_on=True)

def mk_beaker_task(rpm_name):
    # FIXME: proper RHTS launcher shold go here.
    # create a script to: check, install and run a test
    # should task have an "envelope" - e.g. binary to run...
    e = RPMInstaller(rpm_name)
    e.make()
    return e.executable

class RHTSTask(ShExecutable):

    def __init__(self, env_, repos):
        self.__env = env_
        self.__repos = repos
        ShExecutable.__init__(self)

    def content(self):
        self.write_line("""
# THIS SHOULD PREVENT rhts-test-runner.sh to install rpm from default rhts
# repository and use repositories defined in recipe
#mkdir -p $TESTPATH
yum -y --disablerepo=* %s install $TESTRPMNAME
beah-rhts-task
#%s -m beah.tasks.rhts_xmlrpc
""" % (' '.join(['--enablerepo=%s' % repo for repo in self.__repos]),
                sys.executable))


def mk_rhts_task(env_, repos):
    e = RHTSTask(env_, repos)
    e.make()
    return e.executable

def normalize_rpm_name(rpm_name):
    if rpm_name[-4:] != '.rpm':
        return rpm_name
    return rpm_name[:-4]

def xml_attr(node, key, default=None):
    try:
        return str(node.attributes[key].value)
    except:
        return default

def parse_recipe_xml(input_xml):

    root = minidom.parseString(input_xml)
    er = root.firstChild
    task_env = {}

    rs = xml_attr(er, 'status')
    if rs not in ['Running', 'Waiting']:
        log.info("parse_recipe_xml: This recipe has finished.")
        return None

    dict_update(task_env, 
            ARCH=xml_attr(er, 'arch'),
            RECIPEID=xml_attr(er, 'id'),
            JOBID=xml_attr(er, 'job_id'),
            RECIPESETID=xml_attr(er, 'recipe_set_id'),
            HOSTNAME=xml_attr(er, 'system'))

    # FIXME: This will eventually need to be replaced by sth RPM independent...
    repos = []
    repof = ''
    for r in er.getElementsByTagName('repo'):
        name = xml_attr(r, 'name')
        repos.append(name)
        repof += "[%s]\nname=beaker provided '%s' repo\nbaseurl=%s\nenabled=1\ngpgcheck=0\n\n" \
                % (name, name, xml_attr(r, 'url'))
    if repof:
        f = open('/etc/yum.repos.d/beaker-tests.repo', 'w+')
        f.write(repof)
        f.close()
    task_env['BEAKER_REPOS']=':'.join(repos)

    test_order = 0

    for task in er.getElementsByTagName('task'):

        to = xml_attr(task, 'testorder')
        if to is not None:
            test_order = int(to)
        else:
            test_order += 1

        ts = xml_attr(task, 'status')

        if ts not in ['Waiting', 'Running']:
            log.debug("task id: %r status: %r", xml_attr(task, 'id'), ts)
            continue

        task_id = xml_attr(task, 'id')
        task_name = xml_attr(task, 'name')
        dict_update(task_env,
                TASKID=str(task_id),
                RECIPETESTID=str(task_id),
                TESTID=str(task_id),
                TASKNAME=task_name,
                ROLE=xml_attr(task, 'role'))

        # FIXME: Anything else to save?

        for p in task.getElementsByTagName('param'):
            task_env[xml_attr(p, 'name')]=xml_attr(p, 'value')

        for r in task.getElementsByTagName('role'):
            role = []
            for s in r.getElementsByTagName('system'):
                role.append(xml_attr(s, 'value'))
            task_env[xml_attr(r, 'value')]=' '.join(role)

        ewd = xml_attr(task, 'avg_time')
        task_env['KILLTIME'] = ewd

        executable = ''
        args = []
        while not executable:

            rpm_tags = task.getElementsByTagName('rpm')
            log.debug("parse_recipe_xml: rpm tag: %s", rpm_tags)
            if rpm_tags:
                rpm_name = xml_attr(rpm_tags[0], 'name')
                dict_update(task_env,
                        TEST=task_name,
                        TESTRPMNAME=normalize_rpm_name(rpm_name),
                        TESTPATH="/mnt/tests"+task_name ,
                        KILLTIME=str(ewd))
                executable = mk_rhts_task(task_env, repos)
                args = [rpm_name]
                log.info("parse_recipe_xml: RPMTest %s - %s %s", rpm_name, executable, args)
                break

            exec_tags = task.getElementsByTagName('executable')
            log.debug("parse_recipe_xml: executable tag: %s", exec_tags)
            if exec_tags:
                executable = xml_attr(exec_tag[0], 'url')
                for arg in exec_tag[0].getElementsByTagName('arg'):
                    args.append(xml_attr(arg, 'value'))
                log.info("parse_recipe_xml: ExecutableTest %s %s", executable, args)
                break

            break

        proto_len = executable.find(':')
        if proto_len >= 0:
            proto = executable[:proto_len]
            if proto == "file" and executable[proto_len+1:proto_len+3] == '//':
                executable = executable[proto_len+3:]
            else:
                # FIXME: retrieve a file and set an executable bit.
                log.warning("parse_recipe_xml: Feature not implemented yet. proto=%s",
                        proto)
                continue
        else:
            executable = os.path.abspath(executable)

        if not executable:
            log.warning("parse_recipe_xml: Task %s(%s) does not have an executable associated!",
                    task_name, task_id)
            continue

        if task_env.has_key('TESTORDER'):
            task_env['TESTORDER'] = 'TSK_' + task_env['TESTORDER']
        else:
            task_env['TESTORDER'] = 'RCP_' + str(test_order)
        return dict(task_env=task_env, executable=executable, args=args,
                ewd=ewd)

    return None

def handle_error(result, *args, **kwargs):
    log.warning("Deferred Failed(%r, *%r, **%r)", result, args, kwargs)
    return result

# FIXME: Extract this to twmisc!
class LoggingProxy(Proxy):

    verbose_cls = False

    def make_verbose(cls):
        cls.callRemote = print_this(cls.callRemote)
        cls.verbose_cls = True
    make_verbose = classmethod(make_verbose)

    def print_(fmt, *args, **kwargs):
        print fmt % args, kwargs

    def log(self, result, message, method, args, kwargs):
        self.print_("XML-RPC call %s %s: %s", method, message, result)
        self.print_("original call: %s(*%r, **%r)", method, args, kwargs)
        return result

    log_err = log

    def callRemote(self, method, *args, **kwargs):
        return Proxy.callRemote(self, method, *args, **kwargs) \
                .addCallbacks(self.log, self.log_err,
                        callbackArgs=["returned", method, args, kwargs],
                        errbackArgs=["failed", method, args, kwargs])

class BeakerLCBackend(ExtBackend):

    GET_RECIPE = 'get_recipe'
    TASK_START = 'task_start'
    TASK_STOP = 'task_stop'
    TASK_RESULT = 'task_result'

    def __init__(self):
        self.waiting_for_lc = False
        self.__commands = {}
        self.__results_by_uuid = {}
        self.__file_info = {}

    verbose_cls = False

    def make_verbose(cls):
        cls.on_idle = print_this(cls.on_idle)
        cls.on_lc_failure = print_this(cls.on_lc_failure)
        cls.set_controller = print_this(cls.set_controller)
        cls.handle_new_task = print_this(cls.handle_new_task)
        cls.save_command = print_this(cls.save_command)
        cls.get_command = print_this(cls.get_command)
        cls.proc_evt_echo = print_this(cls.proc_evt_echo)
        cls.proc_evt_start = print_this(cls.proc_evt_start)
        cls.proc_evt_end = print_this(cls.proc_evt_end)
        cls.proc_evt_result = print_this(cls.proc_evt_result)
        cls.proc_evt_file = print_this(cls.proc_evt_file)
        cls.proc_evt_file_meta = print_this(cls.proc_evt_file_meta)
        cls.proc_evt_file_write = print_this(cls.proc_evt_file_write)
        cls.handle_Stop = print_this(cls.handle_Stop)
        cls.get_file_info = print_this(cls.get_file_info)
        cls.set_file_info = print_this(cls.set_file_info)
        cls.get_result_id = print_this(cls.get_result_id)
        cls.handle_Result = print_this(cls.handle_Result)
        cls.verbose_cls = True
    make_verbose = classmethod(make_verbose)

    def on_lc_failure(self, result):
        self.waiting_for_lc = False
        log.error(traceback.format_tb(result.getTracebackObject()))
        reactor.callLater(120, self.on_idle)
        return None

    def on_idle(self):
        if self.waiting_for_lc:
            self.on_error("on_idle called with waiting_for_lc already set.")
            return

        hostname = self.conf.get('DEFAULT', 'HOSTNAME')
        self.proxy.callRemote(self.GET_RECIPE, hostname) \
                .addCallback(self.handle_new_task) \
                .addErrback(self.on_lc_failure)
        self.waiting_for_lc = True

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        if controller:
            self.conf = config.config('BEAH_BEAKER_CONF', 'beah_beaker.conf',
                    {
                        'HOSTNAME': os.getenv('HOSTNAME'),
                        'LAB_CONTROLLER': os.getenv('LAB_CONTROLLER',
                            'http://%s:8000/server' %
                            os.getenv('COBBLER_SERVER', 'localhost'))})
            url = self.conf.get('DEFAULT', 'LAB_CONTROLLER')
            self.proxy = LoggingProxy(url)
            if self.verbose_cls:
                self.proxy.make_verbose()
            self.proxy.print_ = log.info
            self.on_idle()

    def handle_new_task(self, result):

        self.waiting_for_lc = False

        log.debug("handle_new_task(%s)", result)

        self.recipe_xml = result

        try:
            self.task_data = parse_recipe_xml(self.recipe_xml)
        except:
            self.on_exception("parse_recipe_xml Failed: %s", format_exc())
            raise

        log.debug("handle_new_task: task_data = %r", self.task_data)

        if self.task_data is None:
            log.info("* Recipe done. Nothing to do...")
            reactor.callLater(60, self.on_idle)
            return

        run_cmd = command.run(self.task_data['executable'],
                env=self.task_data['task_env'],
                args=self.task_data['args'])
        self.controller.proc_cmd(self, run_cmd)
        self.save_command(run_cmd)

        # Persistent env (handled by Controller?) - env to run task under,
        # task can change it, and when restarted will continue with same
        # env(?) Task is able to handle this itself. Provide a library...

    def stop_type(rc):
        if rc==0:
            return "stop"
        return "cancel"
    stop_type = staticmethod(stop_type)

    RESULT_TYPE = {
            RC.PASS:("pass_", "Pass"),
            RC.WARNING:("warn", "Warning"),
            RC.FAIL:("fail", "Fail"),
            RC.CRITICAL:("panic", "Panic - Critical"),
            RC.FATAL:("panic", "Panic - Fatal"),
            }

    def result_type(rc):
        return BeakerLCBackend.RESULT_TYPE.get(rc,
                ("warn", "Warning: Unknown Code (%s)" % rc))
    result_type = staticmethod(result_type)

    def mk_msg(self, **kwargs):
        return json.dumps(kwargs)

    def get_task_id(self, evt):
        return str(self.task_data['task_env']['TASKID'])

    def save_command(self, cmd):
        self.__commands[cmd.id()] = cmd

    def get_command(self, cmd_id):
        return self.__commands.get(cmd_id, None)

    def proc_evt_echo(self, evt):
        cmd = self.get_command(evt.arg('cmd_id'))
        if (cmd is not None and cmd.command()=='run'):
            rc = evt.arg('rc')
            if rc!=ECHO.OK:
                # FIXME: Start was not issued. Is it OK?
                self.proxy.callRemote(self.TASK_STOP,
                        self.get_task_id(evt),
                        # FIXME: This is not correct, is it?
                        self.stop_type("Cancel"),
                        self.mk_msg(reason="Harness could not run the task.",
                            event=evt)) \
                                    .addCallback(self.handle_Stop)
                                    # FIXME: addErrback(...) needed!

    def proc_evt_start(self, evt):
        self.proxy.callRemote(self.TASK_START, self.get_task_id(evt), 0)
        # FIXME: start local watchdog

    def proc_evt_end(self, evt):
        self.proxy.callRemote(self.TASK_STOP,
                self.get_task_id(evt),
                self.stop_type(evt.arg("rc", None)),
                self.mk_msg(event=evt)) \
                        .addCallback(self.handle_Stop)
                        # FIXME: addErrback(...) needed!

    def proc_evt_result(self, evt):
        try:
            self.proxy.callRemote(self.TASK_RESULT,
                    self.get_task_id(evt),
                    self.result_type(evt.arg("rc", None))[0],
                    evt.arg("handle", "%s/%s" % \
                            (self.task_data['task_env']['TASKNAME'], evt.id())),
                    evt.arg("statistics", {}).get("score", 0),
                    self.mk_msg(event=evt)) \
                            .addCallback(self.handle_Result, event_id=evt.id())
        except:
            s = format_exc()
            log.error("Exception in proc_evt_result: %s", s)
            print s
            raise
        # FIXME: add caching events here! While waiting for result, we do not
        # want to submit events, not to change their order.

    def __on_error(self, level, msg, tb, *args, **kwargs):
        if args: msg += '; *args=%r' % (args,)
        if kwargs: msg += '; **kwargs=%r' % (kwargs,)
        log.error("--- %s: %s at %s", level, msg, tb)

    def on_exception(self, msg, *args, **kwargs):
        self.__on_error("EXCEPTION", msg, format_exc(),
                *args, **kwargs)

    def on_error(self, msg, *args, **kwargs):
        self.__on_error("ERROR", msg, traceback.format_stack(), *args, **kwargs)

    def on_warning(self, msg, *args, **kwargs):
        self.__on_error("WARNING", msg, traceback.format_stack(),
                *args, **kwargs)

    def proc_evt_file(self, evt):
        fid = evt.id()
        if self.get_file_info(fid) is not None:
            self.on_error("File with given id (%s) already exists." % fid)
            return
        # FIXME: Check what's submitted:
        self.set_file_info(fid, evt.args())

    def proc_evt_file_meta(self, evt):
        fid = evt.arg('file_id')
        # FIXME: Check what's submitted:
        self.set_file_info(fid, evt.args())

    def proc_evt_file_write(self, evt):
        fid = evt.arg('file_id')
        finfo = addict(self.get_file_info(fid))
        finfo['codec'] = evt.arg('codec', None)
        codec = finfo.get('codec', None)
        offset = evt.arg('offset', None)
        seqoff = finfo.get('offset', 0)
        if offset is None:
            offset = seqoff
        elif offset != seqoff:
            self.on_error(self, "Given offset (%s) does not match calculated (%s)."
                    % (offset, seqoff))
        data = evt.arg('data')
        try:
            cdata = event.decode(codec, data)
        except:
            self.on_exception("Unable to decode data.")
            return
        if cdata is None:
            self.on_error("No data found.")
            return
        size = len(cdata)
        self.set_file_info(fid, offset=offset+size)
        digest = evt.arg('digest', None)
        if digest is None or digest[0] != 'md5':
            d = hashlib.md5()
            d.update(cdata)
            digest = ('md5', d.hexdigest())
        if codec != "base64":
            data = event.encode("base64", cdata)
        filename = finfo.get('name',
                self.task_data['task_env']['TASKNAME'] + '/' + fid)
        #(path, filename) = ('/' + filename).rsplit('/', 1)
        filename = '/' + filename
        sep_ix = filename.rfind('/')
        (path, filename) = (filename[:sep_ix], filename[sep_ix+1:])
        self.proxy.callRemote('task_upload_file', self.get_task_id(evt),
                path[1:] or '/', filename,
                str(size), digest[1], str(offset), data)

    def handle_Stop(self, result):
        """Handler for task_stop XML-RPC return."""
        log_flush(log)
        self.on_idle()

    def get_file_info(self, id):
        """Get a data associated with file. Find file by UUID."""
        return self.__file_info.get(id, None)

    def set_file_info(self, id, *args, **kwargs):
        """Attach a data to file. Find file by UUID."""
        finfo = self.__file_info.setdefault(id, addict())
        for d in args:
            finfo.update(d)
        finfo.update(kwargs)

    def get_result_id(self, event_id):
        """Get a data associated with result. Find result by UUID."""
        self.__results_by_uuid.get(event_id, None)

    def handle_Result(self, result_id, event_id=None):
        """Attach a data to a result. Find result by UUID."""
        log.debug("%s.RETURN: %s (original event_id %s)",
                self.TASK_RESULT, result_id, event_id)
        self.__results_by_uuid[event_id] = result_id

    def close(self):
        # FIXME: send a bye to server? (Should this be considerred an abort?)
        reactor.callLater(1, reactor.stop)

def start_beaker_backend():
    if config.parse_bool(conf.get('BACKEND', 'DEVEL')):
        BeakerLCBackend.make_verbose()
    backend = BeakerLCBackend()
    # Start a default TCP client:
    start_backend(backend, byef=lambda evt: reactor.callLater(1, reactor.stop))

def main():
    start_beaker_backend()
    reactor.run()

if __name__ == '__main__':
    main()

