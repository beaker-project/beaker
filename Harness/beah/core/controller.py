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
from beah.misc import Raiser
from beah import config
from beah.misc.log_this import log_this

################################################################################
# Logging:
################################################################################
log = logging.getLogger('beacon')

# FIXME: !!!
conf = config.main_config()

if config.parse_bool(conf.get('CONTROLLER', 'CONSOLE_LOG')):
    def log_print(level, args, kwargs):
        """Redirect log messages - to stdout"""
        print level, args[0] % args[1:]
else:
    def log_print(level, args, kwargs):
        """Redirect log messages - to /dev/null"""
        pass

def mklog(level, logf):
    """Create a wrapper for logging."""
    def log_w_level(*args, **kwargs):
        """Log wrapper - redirect log message and log it."""
        log_print(level, args, kwargs)
        return logf(*args, **kwargs)
    return log_w_level

log_debug   = mklog("--- DEBUG:   ", log.debug)
log_info    = mklog("--- INFO:    ", log.info)
log_warning = mklog("--- WARNING: ", log.warning)
log_error   = mklog("--- ERROR:   ", log.error)

# INFO: This is for debugging purposes only - allows tracing functional calls
fcall_log = log_this(log_debug,
        config.parse_bool(conf.get('CONTROLLER', 'DEVEL')))

################################################################################
# Controller class:
################################################################################
from beah.core.errors import ServerKilled
class Controller(object):
    """Controller class. Processing commands and events. Creating tasks."""

    __origin = {'class':'controller'}
    __tid = 0

    __ON_KILLED = staticmethod(Raiser(ServerKilled, "Aaargh, I was killed!"))

    def __init__(self, spawn_task, on_killed=None):
        self.spawn_task = spawn_task
        self.tasks = []
        self.backends = []
        self.out_backends = []
        self.conf = {}
        self.killed = False
        self.on_killed = on_killed or self.__ON_KILLED

    def add_backend(self, backend):
        if backend and not (backend in self.backends):
            self.backends.append(backend)
            self.out_backends.append(backend)
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
            if 'task_info' not in dir(task):
                task.task_info = {}
            if 'origin' not in dir(task):
                task.origin = {}
            if not task.origin.has_key('task_info'):
                task.origin['task_info'] = task.task_info

            self.tasks.append(task)
            return True

    def remove_task(self, task):
        if task and task in self.tasks:
            self.tasks.remove(task)
            return True

    def find_task(self, task_id):
        for task in self.tasks:
            if ('task_info' in dir(task) and
                    task.task_info.has_key('id') and
                    task.task_info['id'] == task_id):
                return task
        return None

    def proc_evt(self, task, evt):
        """Process Event received from task.
        
        @task is the Task, which sent the event.
        @evt is an event. Should be an instance of Event class.
        
        This is the only method mandatory for Task side Controller-Adaptor."""
        log_debug("Controller: proc_evt(..., %r)", evt)
        if evt.event() == 'introduce':
            # FIXME: find a task by id and set task.task_info
            task_id = evt.arg('id')
            task.origin['source'] = "socket"
            a_task = self.find_task(task_id)
            if a_task:
                task.task_info = a_task.task_info
            else:
                log_error("Controller: No task %s", task_id)
                task.task_info = dict(id=-1, claimed_id=task_id)
            task.origin['task_info'] = task.task_info
            return
        # controller - spawn_task
        orig = evt.origin()
        if not orig.has_key('task_info'):
            orig['task_info'] = dict(task.origin)
        orig['task_info'].update(task.task_info)
        self.send_evt(evt)

    def send_evt(self, evt, to_all=False):
        #cmd_str = "%s\n" % json.dumps(evt)
        backends = self.out_backends if not to_all else self.backends
        for backend in backends:
            try:
                backend.proc_evt(evt)
            except:
                self.handle_exception("Writing to backend %r failed." % backend)

    def task_started(self, task):
        self.add_task(task)
        self.generate_evt(event.start(task.task_info))

    def task_finished(self, task, rc):
        self.generate_evt(event.end(task.task_info, rc))
        self.remove_task(task)

    def handle_exception(self, message="Exception raised."):
        log_error("Controller: %s %s", message, traceback.format_exc())

    def proc_cmd(self, backend, cmd):
        """Process Command received from backend.

        @backend is the backend, which issued the command.
        @cmd is a command. Should be an instance of Command class.
        
        This is the only method mandatory for Backend side
        Controller-Adaptor."""
        log_debug("Controller: proc_cmd(..., %r)", cmd)
        handler = None
        hana = "proc_cmd_"+cmd.command()
        if hana in dir(self):
            handler = self.__getattribute__(hana)
        if not handler:
            evt = event.echo(cmd, ECHO.NOT_IMPLEMENTED, origin=self.__origin)
        else:
            evt = event.echo(cmd, ECHO.OK, origin=self.__origin)
            try:
                handler(backend, cmd, evt)
            except:
                self.handle_exception("Handling %s raised an exception." %
                        cmd.command())
                evt.args().update(rc=ECHO.EXCEPTION,
                        exception=traceback.format_exc())
        log_debug("Controller: echo(%r)", evt)
        backend.proc_evt(evt)

    def generate_evt(self, evt, to_all=False):
        """Send a new generated event.

        Use this method for sending newly generated events, i.e. not an echo,
        and not when forwarding events from tasks.
        
        to_all - if True, send to all backends, including no_output BE's
        """
        log_debug("Controller: generate_evt(..., %r, %r)", evt, to_all)
        self.send_evt(evt, to_all)

    def proc_cmd_ping(self, backend, cmd, echo_evt):
        evt = event.event('pong', message=cmd.arg('message', None))
        log_debug("Controller: backend.proc_evt(%r)", evt)
        backend.proc_evt(evt)

    def proc_cmd_PING(self, backend, cmd, echo_evt):
        self.generate_evt(event.event('PONG', message=cmd.arg('message', None)))

    def proc_cmd_config(self, backend, cmd, echo_evt):
        self.conf.update(cmd.args())

    def proc_cmd_run(self, backend, cmd, echo_evt):
        # FIXME: assign unique id:
        task_info = dict(cmd.arg('task_info'))
        task_info['id'] = self.__tid
        echo_evt.args()['task_id'] = self.__tid
        self.__tid += 1
        task_env = dict(cmd.arg('env') or {})
        task_args = list(cmd.arg('args') or [])
        self.spawn_task(self, backend, task_info, task_env, task_args)

    def proc_cmd_kill(self, backend, cmd, echo_evt):
        # FIXME: are there any running tasks? - expects kill --force
        # FIXME: [optional] broadcast SIGINT to children
        # FIXME: [optional] add timeout - if there are still some backends
        # running, close anyway...
        self.killed = True
        self.generate_evt(event.event('bye', message='killed'), to_all=True)
        self.on_killed()

    def proc_cmd_dump(self, backend, cmd, echo_evt):
        answ = ""

        answ += "\n== Backends ==\n"
        if self.backends:
            for be in self.backends:
                str = " " if be in self.out_backends else "-"
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

        if self.killed:
            answ += "\n== Killed ==\nTrue\n"

        evt = event.event(event.event('dump', message=answ))
        log_debug("Controller: backend.proc_evt(%r)", evt)
        backend.proc_evt(evt)

        log_info('%s', answ)

    def proc_cmd_no_input(self, backend, cmd, echo_evt):
        pass

    def proc_cmd_no_output(self, backend, cmd, echo_evt):
        # FIXME: Do not delete from backends. There should be a list of all
        # backends, for broadcast - e.g. bye event.
        if backend in self.out_backends:
            self.out_backends.remove(backend)

