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

import traceback
import exceptions
import logging
from beah.core import event, command
from beah.core.constants import ECHO
from beah.misc import Raiser, localhost, format_exc, dict_update, log_flush
from beah import config

from beah.system import Executable

################################################################################
# Logging:
################################################################################
log = logging.getLogger('beah')

################################################################################
# Controller class:
################################################################################
from beah.core.errors import ServerKilled
class Controller(object):
    """Controller class. Processing commands and events. Creating tasks."""

    __origin = {'class':'controller'}

    __ON_KILLED = staticmethod(Raiser(ServerKilled, "Aaargh, I was killed!"))
    _VERBOSE = ('add_backend', 'remove_backend', 'add_task', 'remove_task',
            'find_task', 'proc_evt', 'send_evt', 'task_started',
            'task_finished', 'handle_exception', 'proc_cmd', 'generate_evt',
            'proc_cmd_forward', 'proc_cmd_variable_value', 'proc_cmd_ping',
            'proc_cmd_PING', 'proc_cmd_config', 'proc_cmd_run',
            'proc_cmd_run_this', 'proc_cmd_kill', 'proc_cmd_dump',
            'proc_cmd_no_input', 'proc_cmd_no_output')

    def __init__(self, spawn_task, on_killed=None):
        self.spawn_task = spawn_task
        self.tasks = []
        self.backends = []
        self.out_backends = []
        self.conf = {}
        self.killed = False
        self.on_killed = on_killed or self.__ON_KILLED
        self.__waiting_tasks = {}

    def add_backend(self, backend):
        if backend and not (backend in self.backends):
            self.backends.append(backend)
            self.out_backends.append(backend)
            for k, v in self.__waiting_tasks.items():
                backend.proc_evt(v[0])
            return True

    def remove_backend(self, backend):
        if backend and backend in self.backends:
            self.backends.remove(backend)
            if backend in self.out_backends:
                self.out_backends.remove(backend)
            if self.killed and not self.backends:
                # All backends were removed and controller was killed - call
                # on_killed handler
                self.on_killed()
            return True

    def add_task(self, task):
        if task and not (task in self.tasks):
            if 'origin' not in dir(task):
                task.origin = {}
            if not task.origin.has_key('id'):
                task.origin['id'] = task.task_id

            self.tasks.append(task)
            return True

    def remove_task(self, task):
        if task and task in self.tasks:
            self.tasks.remove(task)
            return True

    def find_task(self, task_id):
        for task in self.tasks:
            if (task.task_id == task_id):
                return task
        return None

    def proc_evt(self, task, evt):
        """
        Process Event received from task.

        @task is the Task, which sent the event.
        @evt is an event. Should be an instance of Event class.

        This is the only method mandatory for Task side Controller-Adaptor.
        """
        log.debug("Controller: proc_evt(..., %r)", evt)
        evev = evt.event()
        if evev == 'introduce':
            task_id = evt.arg('id')
            task.task_id = task_id
            task.origin['source'] = "socket"
            task.origin['id'] = task_id
            if not self.find_task(task_id):
                log.error("Controller: No task %s", task_id)
            return
        elif evev in ['variable_set', 'variable_get']:
            handle = evt.arg('handle', '')
            dest = evt.arg('dest', '')
            key = evt.arg('key')
            if handle == '' and localhost(dest):
                if evev == 'variable_set':
                    self.runtime.vars[key] = evt.arg('value')
                else:
                    if self.runtime.vars.has_key(key):
                        value = self.runtime.vars[key]
                        task.proc_cmd(command.variable_value(key, value,
                            handle=handle, dest=dest))
                return
            else:
                if dest == 'test.loop':
                    dest = ''
                s = repr(("command.variable_value", key, handle, dest))
                if self.__waiting_tasks.has_key(s):
                    _, l = self.__waiting_tasks[s]
                    if task not in l:
                        l.append(task)
                        log.debug("Controller.__waiting_tasks=%r", self.__waiting_tasks)
                    return
                _, l = self.__waiting_tasks[s] = (evt, [task])
                log.debug("Controller.__waiting_tasks=%r", self.__waiting_tasks)
        # controller - spawn_task
        orig = evt.origin()
        if not orig.has_key('id'):
            orig['id'] = task.task_id
        self.send_evt(evt)

    def send_evt(self, evt, to_all=False):
        #cmd_str = "%s\n" % json.dumps(evt)
        if not to_all:
            (backends, flags) = (self.out_backends, {})
        else:
            (backends, flags) = (self.backends, {'broadcast': True})
        for backend in backends:
            try:
                backend.proc_evt(evt, **flags)
            except:
                self.handle_exception("Writing to backend %r failed." % backend)

    def task_started(self, task):
        self.add_task(task)
        self.generate_evt(event.start(task.task_id))

    def task_finished(self, task, rc):
        self.generate_evt(event.end(task.task_id, rc))
        self.remove_task(task)
        log_flush(log)

    def handle_exception(self, message="Exception raised."):
        log.error("Controller: %s %s", message, format_exc())

    def proc_cmd(self, backend, cmd):
        """Process Command received from backend.

        @backend is the backend, which issued the command.
        @cmd is a command. Should be an instance of Command class.

        This is the only method mandatory for Backend side
        Controller-Adaptor."""
        log.debug("Controller: proc_cmd(..., %r)", cmd)
        handler = getattr(self, "proc_cmd_"+cmd.command(), None)
        if not handler:
            evt = event.echo(cmd, ECHO.NOT_IMPLEMENTED, origin=self.__origin)
        else:
            evt = event.echo(cmd, ECHO.OK, origin=self.__origin)
            try:
                handler(backend, cmd, evt)
            except:
                self.handle_exception("Handling %s raised an exception." %
                        cmd.command())
                dict_update(evt.args(),
                        rc=ECHO.EXCEPTION,
                        exception=format_exc())
        log.debug("Controller: echo(%r)", evt)
        backend.proc_evt(evt, explicit=True)

    def generate_evt(self, evt, to_all=False):
        """Send a new generated event.

        Use this method for sending newly generated events, i.e. not an echo,
        and not when forwarding events from tasks.

        to_all - if True, send to all backends, including no_output BE's
        """
        log.debug("Controller: generate_evt(..., %r, %r)", evt, to_all)
        self.send_evt(evt, to_all)

    class BackendFakeTask(object):
        def __init__(self, controller, backend, forward_id):
            self.controller = controller
            self.backend = backend
            self.forward_id = forward_id
            self.origin = {'signature':'BackendFakeTask'}
            self.task_id = 'no-id'

        def proc_cmd(self, cmd):
            evt = event.forward_response(cmd, self.forward_id)
            self.backend.proc_evt(evt, explicit=True)

    def proc_cmd_forward(self, backend, cmd, echo_evt):
        evt = event.event(cmd.arg('event'))
        evev = evt.event()
        # FIXME: incomming events filter - CHECK
        if evev not in ['variable_get', 'variable_set']:
            echo_evt.args['rc'] = ECHO.EXCEPTION
            echo_evt.args['message'] = 'Event %r is not permitted here.' % evev
            return
        fake_task = self.BackendFakeTask(self, backend, cmd.id())
        self.proc_evt(fake_task, evt)

    def proc_cmd_variable_value(self, backend, cmd, echo_evt):
        s = repr(("command.variable_value", cmd.arg("key"), cmd.arg("handle"), cmd.arg("dest")))
        _, l = self.__waiting_tasks.get(s, (None, None))
        log.debug("Controller.__waiting_tasks[%r]=%r", s, l)
        if l is not None:
            for task in l:
                log.debug("Controller: %s.proc_cmd(%r)", task, cmd)
                task.proc_cmd(cmd)
            del self.__waiting_tasks[s]
        log.debug("Controller.__waiting_tasks=%r", self.__waiting_tasks)

    def proc_cmd_ping(self, backend, cmd, echo_evt):
        evt = event.Event('pong', message=cmd.arg('message', None))
        log.debug("Controller: backend.proc_evt(%r)", evt)
        backend.proc_evt(evt, explicit=True)

    def proc_cmd_PING(self, backend, cmd, echo_evt):
        self.generate_evt(event.Event('PONG', message=cmd.arg('message', None)))

    def proc_cmd_config(self, backend, cmd, echo_evt):
        self.conf.update(cmd.args())

    def proc_cmd_run(self, backend, cmd, echo_evt):
        task_info = dict(cmd.arg('task_info'))
        task_id = cmd.id()
        if self.find_task(task_id) is not None:
            echo_evt.args['rc'] = ECHO.DUPLICATE
            echo_evt.args['message'] = 'The task with id == %r is already running.' % task_id
            return
        task_info['id'] = task_id
        # FIXME!!! save task_info
        task_env = dict(cmd.arg('env') or {})
        task_args = list(cmd.arg('args') or [])
        self.spawn_task(self, backend, task_info, task_env, task_args)

    def proc_cmd_run_this(self, backend, cmd, echo_evt):
        # FIXME: This looks dangerous! Is future BE filter enough? Disable!
        se = Executable()
        # FIXME: windows? need different ext and different default.
        se.content = lambda: se.write_line(cmd.arg('script', "#!/bin/sh\nexit 1"))
        se.make()
        task_info = dict(cmd.arg('task_info'))
        task_info['id'] = cmd.id()
        task_info['file'] = se.executable
        # FIXME!!! save task_info
        task_env = dict(cmd.arg('env') or {})
        task_args = list(cmd.arg('args') or [])
        self.spawn_task(self, backend, task_info, task_env, task_args)

    def proc_cmd_kill(self, backend, cmd, echo_evt):
        # FIXME: are there any running tasks? - expects kill --force
        # FIXME: [optional] broadcast SIGINT to children
        # FIXME: [optional] add timeout - if there are still some backends
        # running, close anyway...
        self.killed = True
        self.generate_evt(event.Event('bye', message='killed'), to_all=True)
        self.on_killed()

    def proc_cmd_dump(self, backend, cmd, echo_evt):
        answ = ""

        answ += "\n== Backends ==\n"
        if self.backends:
            for be in self.backends:
                if be:
                    str = " "
                else:
                    str = "-"
                answ += "%s %s\n" % (str, be)
        else:
            answ += "None\n"

        answ += "\n== Tasks ==\n"
        if self.tasks:
            for t in self.tasks:
                answ += "%s\n" % t
        else:
            answ += "None\n"

        if self.conf:
            answ += "\n== Config ==\n%s\n" % (self.conf,)

        if self.runtime.vars:
            answ += "\n== Variables ==\n"
            for k in sorted(self.runtime.vars.keys()):
                answ += "%r=%r\n" % (k, self.runtime.vars[k])

        if self.killed:
            answ += "\n== Killed ==\nTrue\n"

        evt = event.Event('dump', message=answ)
        log.debug("Controller: backend.proc_evt(%r)", evt)
        backend.proc_evt(evt, explicit=True)

        log.info('%s', answ)

    def proc_cmd_no_input(self, backend, cmd, echo_evt):
        pass

    def proc_cmd_no_output(self, backend, cmd, echo_evt):
        if backend in self.out_backends:
            self.out_backends.remove(backend)

