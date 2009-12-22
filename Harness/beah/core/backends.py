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

from beah.core.errors import KilledException
class GoodBye(KilledException): pass

class BasicBackend(object):
    """Simple Backend, with no command input."""
    def __init__(self):
        self.controller = None
    def set_controller(self, controller=None):
        self.controller = controller
    def proc_evt(self, evt, **flags):
        if "proc_evt_"+evt.event() in dir(self):
            try:
                self.__getattribute__("proc_evt_"+evt.event())(evt)
            except:
                # FIXME: log error
                pass
            return True
        return False
    def proc_evt_bye(self, evt):
        raise GoodBye("Controller said: \"bye\".")
    def close(self):
        pass

class ExtBackend(BasicBackend):
    def pre_proc(self, evt):
        return False
    def post_proc(self, evt, answ):
        return answ
    def proc_evt(self, evt, **flags):
        if self.pre_proc(evt):
            return True
        answ = BasicBackend.proc_evt(self, evt, **flags)
        return self.post_proc(evt, answ)

import pprint
class PprintBackend(ExtBackend):
    def pre_proc(self, evt):
        pprint.pprint(evt)
        return False

from simplejson import dumps
class PrintBackend(ExtBackend):
    def pre_proc(self, evt):
        print dumps(evt)
        return False

from sys import stderr
from beah.filters.cmdfilter import CmdFilter
from beah.core.constants import ECHO
class CmdBackend(ExtBackend):
    from sys import stdout

    def __init__(self):
        self.cf = CmdFilter()
        self.wait = False
        ExtBackend.__init__(self)

    def connection_made(self):
        print "\n" + self.prompt(),
        self.stdout.flush()

    def line_received(self, line):
        self.proc_input(line)
        if not self.wait:
            print self.prompt(),
            self.stdout.flush()

    def prompt(self):
        if self.controller:
            return "beacon> "
        else:
            return "waiting for controller... "

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        print "\n" + self.prompt(),
        self.stdout.flush()

    def proc_input(self, data):
        if not self.wait:
            cmd = self.cf.proc_line(data)
            if cmd:
                self.controller.proc_cmd(self, cmd)
                self.wait = True
        else:
            print "busy. waiting for echo..."

    def proc_evt_echo(self, evt):
        if self.wait:
            try:
                self.wait = False
                if evt.args()['rc'] == ECHO.OK:
                    print "OK"
                    return
                if evt.args()['rc'] == ECHO.NOT_IMPLEMENTED:
                    print "--- ERROR: Command is not implemented."
                    return
                if evt.args()['rc'] == ECHO.EXCEPTION:
                    print "--- ERROR: Command raised an exception."
                    print evt.args()['exception']
                    return
            finally:
                print self.prompt(),
                self.stdout.flush()

    def post_proc(self, evt, answ):
        if self.wait:
            pprint.pprint(evt)
        return answ

from beah.core import command
class CmdOnlyBackend(CmdBackend):
    def set_controller(self, controller=None):
        CmdBackend.set_controller(self, controller)
        if controller:
            self.controller.proc_cmd(self, command.no_output())


################################################################################
# TESTING:
################################################################################
if __name__ == '__main__':
    import exceptions
    be = CmdOnlyBackend()
    class FakeController(object):
        def __init__(self, expected=None):
            self.expected = expected
        def proc_cmd(self, backend, cmd):
            if cmd != self.expected:
                raise exceptions.Exception('got %r, expected %r' % (cmd, self.expected))
    be.set_controller(FakeController(command.no_output()))
    def test(be, input, output):
        be.controller.expected = output
        be.proc_input(input)
    test(be, 'ping', command.ping())
    test(be, 'PING a message', command.PING('a message'))
    test(be, 'run a_task', command.run('a_task'))
    print "This is likely an expected failure - task id changes over the time..."

