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

import exceptions

class ControllerInterface(object):
    """Classes used as a Controller should implement this interface. This
    includes Task and Backend side Controller-Adaptor"""

    def proc_cmd(self, backend, cmd):
        """Process Command received from backend.

        @backend is the backend, which issued the command.
        @cmd is a command. Should be an instance of Command class.

        This is the only method mandatory for Backend side Controller-Adaptor."""
        raise exceptions.NotImplementedError

    def proc_evt(self, task, evt):
        """Process Event received from task.

        @task is the Task, which sent the event.
        @evt is an event. Should be an instance of Event class.

        This is the only method mandatory for Task side Controller-Adaptor."""
        raise exceptions.NotImplementedError

    def add_backend(self, backend):
        raise exceptions.NotImplementedError

    def remove_backend(self, backend):
        raise exceptions.NotImplementedError

    def add_task(self, task):
        raise exceptions.NotImplementedError

    def remove_task(self, task):
        raise exceptions.NotImplementedError

class BackendInterface(object):
    """Class used as a Backend should implement this interface. This includes
    Controller side Backend-Adaptor"""

    def proc_evt(self, evt, **flags):
        """Process event received from task"""
        raise exceptions.NotImplementedError

    def set_controller(self, controller=None):
        raise exceptions.NotImplementedError

class TaskInterface(object):
    """Class used as a Task should implement this interface. This includes
    Controller side Task-Adaptor"""

    def proc_cmd(self, cmd):
        """Process command received from Controller"""
        raise exceptions.NotImplementedError

    def set_controller(self, controller=None):
        raise exceptions.NotImplementedError

