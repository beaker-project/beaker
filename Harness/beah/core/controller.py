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

import traceback, exceptions
from beah.core import event, command
from beah.core.constants import ECHO
from beah.misc import Raiser
from beah import config

################################################################################
# Logging:
################################################################################
import logging
log = logging.getLogger('beacon')

if config.SRV_LOG():
    def log_print(level, args, kwargs):
        print level, args[0] % args[1:]
else:
    def log_print(level, args, kwargs):
        pass

def mklog(level, logf):
    def log_w_level(*args, **kwargs):
        log_print(level, args, kwargs)
        return logf(*args, **kwargs)
    return log_w_level

log_debug   = mklog("--- DEBUG:   ", log.debug)
log_info    = mklog("--- INFO:    ", log.info)
log_warning = mklog("--- WARNING: ", log.warning)
log_error   = mklog("--- ERROR:   ", log.error)

# INFO: This is for debugging purposes only - allows tracing functional calls
from beah.misc.log_this import log_this
fcall_log = log_this(log_debug, config.LOG())

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
        self.config = {}
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
            self.tasks.append(task)
            return True

    def remove_task(self, task):
        if task and task in self.tasks:
            self.tasks.remove(task)
            return True

    def proc_evt(self, task, evt):
        """Process Event received from task.
        
        @task is the Task, which sent the event.
        @evt is an event. Should be an instance of Event class.
        
        This is the only method mandatory for Task side Controller-Adaptor."""
        log_debug("Controller: proc_evt(..., %r)", evt)
        # FIXME: should any processing go here - e.g. task talking to
        # controller - spawn_task
        self.send_evt(evt)

    def send_evt(self, evt, all=False):
        #cmd_str = "%s\n" % json.dumps(evt)
        backends = self.out_backends if not all else self.backends
        for backend in backends:
            try:
                backend.proc_evt(evt)
            except:
                self.handle_exception("Writing to backend %r failed." % backend)

    def task_started(self, task):
        self.add_task(task)
        self.send_evt(event.start(task.task_info))

    def task_finished(self, task, rc):
        self.send_evt(event.end(task.task_info, rc))
        self.remove_task(task)

    def handle_exception(self, message="Exception raised."):
        log_error("Controller: %s %s", message, traceback.format_exc())

    def proc_cmd(self, backend, cmd):
        """Process Command received from backend.

        @backend is the backend, which issued the command.
        @cmd is a command. Should be an instance of Command class.
        
        This is the only method mandatory for Backend side Controller-Adaptor."""
        log_debug("Controller: proc_cmd(..., %r)", cmd)
        try:
            handler = self.__getattribute__("proc_cmd_"+cmd.command())
        except:
            backend.proc_evt(event.echo(cmd, ECHO.NOT_IMPLEMENTED,
                origin=self.__origin))
            return
        try:
            handler(backend, cmd)
            backend.proc_evt(event.echo(cmd, ECHO.OK, origin=self.__origin))
        except:
            self.handle_exception("Command %s raised an exception." %
                    cmd.command())
            backend.proc_evt(event.echo(cmd, rc=ECHO.EXCEPTION,
                origin=self.__origin, exception=traceback.format_exc()))
        # FIXME: Test: will __getattribute__ work correctly on old python's?
        # Use following old code if not:
        #try:
        #    handler = self.__dict__["proc_cmd_"+cmd.command()]
        #except:
        #    try:
        #        handler = self.__class__.__dict__["proc_cmd_"+cmd.command()]
        #    except:
        #        backend.proc_evt(event.echo(cmd, ECHO.NOT_IMPLEMENTED,
        #            origin=self.__origin))
        #        return
        #try:
        #    handler(self, backend, cmd)
        #    backend.proc_evt(event.echo(cmd, ECHO.OK, origin=self.__origin))
        #except:
        #    self.handle_exception("Command %s raised an exception." %
        #            cmd.command())
        #    backend.proc_evt(event.echo(cmd, rc=ECHO.EXCEPTION,
        #        origin=self.__origin, exception=traceback.format_exc()))

    def proc_cmd_ping(self, backend, cmd):
        backend.proc_evt(event.event('pong', message=cmd.arg('message', None)))

    def proc_cmd_PING(self, backend, cmd):
        self.send_evt(event.event('PONG', message=cmd.arg('message', None)))

    def proc_cmd_config(self, backend, cmd):
        self.config.update(cmd.args())

    def proc_cmd_run(self, backend, cmd):
        # FIXME: assign unique id:
        task_info = dict(cmd.arg('task_info'))
        task_info['id'] = self.__tid
        self.__tid += 1
        self.spawn_task(self, backend, task_info)

    def proc_cmd_kill(self, backend, cmd):
        # FIXME: are there any running tasks? - expects kill --force
        # FIXME: [optional] broadcast SIGINT to children
        # FIXME: [optional] add timeout - if there are still some backends running, close
        # anyway...
        self.killed = True
        self.send_evt(event.event('bye', message='killed'), all=True)
        self.on_killed()

    def proc_cmd_dump(self, backend, cmd):
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

        if self.config:
            answ += "\n== Config ==\n%s\n" % (self.config,)

        if self.killed:
            answ += "\n== Killed ==\nTrue\n"

        backend.proc_evt(event.event('dump', message=answ))

        print answ

    def proc_cmd_no_input(self, backend, cmd):
        pass

    def proc_cmd_no_output(self, backend, cmd):
        # FIXME: Do not delete from backends. There should be a list of all
        # backends, for broadcast - e.g. bye event.
        if backend in self.out_backends:
            self.out_backends.remove(backend)

