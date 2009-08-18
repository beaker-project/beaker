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

from beah.core import event, command
from beah.core.errors import KilledException
from beah.wires.internals.twmisc import JSONProtocol

class ControllerAdaptor_Backend_JSON(JSONProtocol):
    def add_backend(self, backend):
        self.backend = backend
        self.backend.set_controller(None) # Wait for connectionMade
    def remove_backend(self, backend):
        self.backend.set_controller(None)
        self.backend = None
    def proc_input(self, cmd):
        """Process data(Event) received from Controller - forward to Backend"""
        if self.backend:
            try:
                self.backend.proc_evt(event.event(cmd))
            except KilledException:
                # FIXME: kill?
                print "Server was killed, should also die..."
                raise
    def proc_cmd(self, backend, cmd):
        """Process Command received from backend - forward to Controller"""
        self.send_cmd(cmd)
    def connectionMade(self):
        if self.backend:
            self.backend.set_controller(self)
    def connectionLost(self, reason):
        if self.backend:
            self.backend.set_controller(None)

class BackendAdaptor_JSON(JSONProtocol):
    def set_controller(self, controller=None):
        self.controller = controller
    def proc_input(self, cmd):
        """Process data(Command) received from Backend - forward to Controller"""
        if self.controller:
            self.controller.proc_cmd(self, command.command(cmd))
    def proc_evt(self, evt):
        """Process Event received from Controller - forward to Backed"""
        self.send_cmd(evt)
    def connectionMade(self):
        if self.controller:
            self.controller.add_backend(self)
    def connectionLost(self, reason):
        if self.controller:
            self.controller.remove_backend(self)

class TaskAdaptor_JSON(JSONProtocol):
    def __init__(self):
        self.origin = {}
    def set_controller(self, controller=None):
        self.controller = controller
    def proc_input(self, cmd):
        """Process data(Event) received from Task - forward to Controller"""
        if not cmd:
            return
        if self.controller:
            try:
                evt = event.event(cmd)
            except:
                evt = event.lose_item(data=cmd, origin=self.origin)
            self.controller.proc_evt(self, evt)
    def lose_item(self, data):
        if self.controller:
            self.controller.proc_evt(self, event.lose_item(data=data,
                origin=self.origin))
    def proc_cmd(self, cmd):
        """Process Command received from Controller - forward to Task"""
        self.send_cmd(cmd)
    def connectionMade(self):
        if self.controller:
            self.controller.add_task(self)
    def connectionLost(self, reason):
        if self.controller:
            self.controller.remove_task(self)

class ControllerAdaptor_Task_JSON(JSONProtocol):
    def add_task(self, task):
        self.task = task
        self.task.set_controller(None) # wait for connectionMade
    def remove_task(self, task):
        self.task.set_controller(None)
        self.task = None
    def proc_input(self, cmd):
        """Process data(Command) received from Controller - forward to Task"""
        if self.task:
            self.task.proc_cmd(command.command(cmd))
    def proc_evt(self, task, evt):
        """Process Event received from Task - forward to Controller"""
        self.send_cmd(evt)
    def connectionMade(self):
        if self.task:
            self.task.set_controller(self)
    def connectionLost(self, reason):
        if self.task:
            self.task.set_controller(None)

