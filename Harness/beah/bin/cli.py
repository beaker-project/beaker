#!/usr/bin/env python

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

from twisted.internet import reactor
from beah.wires.internals.twbackend import start_backend
from beah.core.backends import ExtBackend
from beah.core import command
from beah.core.constants import ECHO
import pprint, exceptions

class CmdLineBackend(ExtBackend):
    def __init__(self, cmdline):
        from beah.filters.cmdfilter import CmdFilter
        self.wait = False
        self.cmd = CmdFilter().proc_line(cmdline)
        if not self.cmd:
            print "--- ERROR: Command error."
            raise exceptions.Exception

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        if controller:
            #controller.proc_cmd(self, command.ping("Are you there?"))
            controller.proc_cmd(self, command.no_output())
            controller.proc_cmd(self, self.cmd)
            self.wait = True

    def proc_evt_bye(self, evt):
        reactor.callLater(1,reactor.stop)

    def proc_evt_echo(self, evt):
        if evt.arg('cmd', ['Command','',{}]) == self.cmd:
            global rc
            try:
                self.wait = False
                if evt.args()['rc'] == ECHO.OK:
                    print "OK"
                    return
                if evt.args()['rc'] == ECHO.NOT_IMPLEMENTED:
                    print "--- ERROR: Command is not implemented."
                    rc = 1
                    return
                if evt.args()['rc'] == ECHO.EXCEPTION:
                    print "--- ERROR: Command raised an exception."
                    print evt.args()['exception']
                    rc = 1
                    return
                return
            finally:
                reactor.callLater(1,reactor.stop)

    def post_proc(self, evt, answ):
        if self.wait:
            pprint.pprint(evt)
        return answ

def main_beah(cmdline):
    """\
This is a Backend to issue commands to Controller.

Type help on the prompt for help o commands.

You might not see any output here - run out_backend.

Known issues:

 * Type <Ctrl-C> to finish.

   I do not want to stop reactor directly, but would like if it stopped if
   there are no more protocols.
"""
    backend = CmdLineBackend(cmdline)
    # Start a default TCP client:
    start_backend(backend)

def main():
    import sys
    rc = 0
    try:
        main_beah(' '.join(sys.argv[1:]))
    except:
        sys.exit(1)
    reactor.run()
    sys.exit(rc)

if __name__ == '__main__':
    main()
