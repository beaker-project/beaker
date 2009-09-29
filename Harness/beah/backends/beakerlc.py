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

import os, exceptions, tempfile, pprint
from xml.etree import ElementTree
import simplejson as json

from beah.core.backends import ExtBackend
from beah.core import command
from beah.core.constants import ECHO, RC
from beah import config

import beah.system
# FIXME: using rpm's, yum - too much Fedora centric(?)
from beah.system.dist_fedora import RPMInstaller

"""
Beaker Backend.

Beaker Backend should invoke these XML-RPC:
 1. recipes.to_xml(recipe_id)
    recipes.system_xml(fqdn)
 2. parse XML
 3. recipes.tasks.Start(task_id, kill_time)
 *. recipes.tasks.Result(task_id, result_type, path, score, summary)
    - result_type: Pass|Warn|Fail|Panic
 4. recipes.tasks.Stop(task_id, stop_type, msg)
    - stop_type: Stop|Abort|Cancel
"""

def mk_beaker_task(rpm_name):
    # FIXME: see rhts-test-runner for ideas:
    # /home/mcsontos/rhts/rhts/test-env-lab/bin/rhts-test-runner.sh

    # create a script to: check, install and run a test
    # should task have an "envelope" - e.g. binary to run...

    # repositories: http://rhts.redhat.com/rpms/{development,production}/noarch/
    # see scratch.tmp/rhts-tests.repo

    # have a look at:
    # http://intranet.corp.redhat.com/ic/intranet/RHTSMainPage.html#devel
    e = RPMInstaller(rpm_name)
    e.make()
    return e.executable

def parse_recipe_xml(input_xml):

    er = ElementTree.fromstring(input_xml)
    task_env = {}

    rs = er.get('status')
    # FIXME: is this condition correct?
    if rs != 'Running' and True:
        print "This recipe has finished."
        return None

    task_env.update(
            RECIPEID=er.get('id'),
            JOBID=er.get('job_id'),
            RECIPESETID=er.get('recipe_set_id'),
            HOSTNAME=er.get('system'))

    for task in er.findall('task'):

        ts = task.get('status')

        # FIXME: is this condition correct?
        #if ts == 'Running':
        #    break
        if ts != 'Waiting' and ts != 'Running':
            continue

        if ts == 'Running':
            # FIXME: A task SHOULD BE already running.
            return None

        task_id = task.get('id')
        task_name = task.get('name')
        task_env.update(
                TASKID=task_id,
                TASKNAME=task_name,
                ROLE=task.get('role'))

        # FIXME: Anything else to save?

        for p in task.getiterator('param'):
            task_env[p.get('name')]=p.get('value')

        for r in task.getiterator('role'):
            role = []
            for s in r.findall('system'):
                role.append(s.get('value'))
            task_env[r.get('value')]=' '.join(role)

        ewd = task.get('avg_time')

        executable = ''
        args = []
        while not executable:

            rpm_tag = task.find('rpm')
            print "rpm tag: %s" % rpm_tag
            if rpm_tag is not None:
                rpm_name = rpm_tag.get('name')
                task_env.update(RPMNAME=rpm_name)
                executable = mk_beaker_task(rpm_name)
                args = [rpm_name]
                print "RPMTest %s - %s %s" % (rpm_name, executable, args)
                break

            exec_tag = task.find('executable')
            print "executable tag: %s" % exec_tag
            if exec_tag is not None:
                executable = exec_tag.get('url')
                for arg in exec_tag.findall('arg'):
                    args.append(arg.get('value'))
                print "ExecutableTest %s %s" % (executable, args)
                break

            break

        proto_len = executable.find(':')
        if proto_len >= 0:
            proto = executable[:proto_len]
            if proto == "file" and executable[proto_len+1:proto_len+3] == '//':
                executable = executable[proto_len+3:]
            else:
                # FIXME: retrieve a file and set an executable bit.
                print "Feature not implemented yet."
                continue

        if not executable:
            print "Task %s(%s) does not have an executable associated!" % \
                    (task_name, task_id)
            continue

        return dict(task_env=task_env, executable=executable, args=args, ewd=ewd)

    return None

class BeakerLCBackend(ExtBackend):

    GET_RECIPE = 'get_recipe'
    TASK_START = 'task_start'
    TASK_STOP = 'task_stop'
    TASK_RESULT = 'task_result'

    def on_idle(self):
        hostname = self.conf.get('DEFAULT', 'HOSTNAME')
        self.proxy.callRemote(self.GET_RECIPE,
                hostname).addCallback(self.handle_new_task)

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        if controller:
            self.conf = config.config('BEAH_BEAKER_CONF', 'beah_beaker.conf',
                    {'HOSTNAME':os.getenv('HOSTNAME')})
            url = self.conf.get('DEFAULT', 'LAB_CONTROLLER')
            self.proxy = Proxy(url)
            self.on_idle()

    def handle_new_task(self, result):
        pprint.pprint(result)

        self.recipe_xml = result

        self.task_data = parse_recipe_xml(self.recipe_xml)
        pprint.pprint(self.task_data)

        if self.task_data is None:
            print "* Recipe done. Nothing to do..."
            reactor.callLater(60, self.on_idle)
            return

        self.controller.proc_cmd(self,
                command.run(self.task_data['executable'],
                    env=self.task_data['task_env'],
                    args=self.task_data['args']))

        # Persistent env (handled by Controller?) - env to run task under,
        # task can change it, and when restarted will continue with same
        # env(?) Task is able to handle this itself. Provide a library...

    def pre_proc(self, evt):
        # FIXME: remove
        pprint.pprint(evt)

    @staticmethod
    def stop_type(rc):
        return "Stop" if rc==0 else "Cancel"

    RESULT_TYPE = {
            RC.PASS:("Pass", "Pass"),
            RC.WARNING:("Warn", "Warning"),
            RC.FAIL:("Fail", "Fail"),
            RC.CRITICAL:("Panic", "Critical"),
            RC.FATAL:("Panic", "Fatal"),
            }
    @staticmethod
    def result_type(rc):
        return self.RESULT_TYPE.get(rc, ("Warn","Unknown Code"))

    def mk_msg(self, **kwargs):
        return json.dumps(kwargs)

    def proc_evt_echo(self, evt):
        if (evt.arg('cmd').command()=='run'):
            rc = echo.arg('rc')
            if rc!=ECHO.OK:
                # FIXME: Start was not issued. Is it OK?
                self.proxy.callRemote(self.TASK_STOP,
                        int(self.task_data['task_env']['TASKID']),
                        self.stop_type("Cancel"),
                        self.mk_msg(reason="Harness could not run the task.", event=evt)).addCallback(self.handle_Stop)

    def proc_evt_start(self, evt):
        self.proxy.callRemote(self.TASK_START,
                int(self.task_data['task_env']['TASKID']),
                0)
        # FIXME: start local watchdog

    def proc_evt_end(self, evt):
        self.proxy.callRemote(self.TASK_STOP,
                int(self.task_data['task_env']['TASKID']),
                self.stop_type(evt.arg("rc",None)),
                self.mk_msg(event=evt)).addCallback(self.handle_Stop)

    def proc_evt_result(self, evt):
        res = self.result_type(evt.arg("rc",None))
        self.proxy.callRemote(self.TASK_RESULT,
                int(self.task_data['task_env']['TASKID']),
                res[0],
                "", # FIXME: path?
                0, # FIXME:score?
                self.mk_msg(event=evt))

    def handle_Stop(self, result):
        self.on_idle()

    def close(self):
        # FIXME: send a bye to server? (Should this be considerred an abort?)
        reactor.callLater(1, reactor.stop)

def start_beaker_backend():
    from beah.wires.internals.twbackend import start_backend
    backend = BeakerLCBackend()
    # Start a default TCP client:
    start_backend(backend, byef=lambda evt: reactor.callLater(1, reactor.stop))

def main():
    start_beaker_backend()
    reactor.run()

if __name__ == '__main__':
    main()

