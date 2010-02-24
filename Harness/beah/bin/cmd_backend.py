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

from beah.wires.internals.twbackend import start_backend, log_handler
from beah.core.backends import CmdOnlyBackend
from beah import config
from twisted.internet import stdio
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
from exceptions import StopIteration

class TwistedCmdBackend(LineReceiver):
    """Read commands from stdin, parse and forward to the Controller.

    FIXME: Use Twsited's Manhole for handling input (history,...)
    See:
        /usr/lib64/python2.5/site-packages/twisted/conch/stdio.py - Example
        /usr/lib64/python2.5/site-packages/twisted/conch/insults/insults.py
        /usr/lib64/python2.5/site-packages/twisted/conch/recvline.py
        /usr/lib64/python2.5/site-packages/twisted/conch/manhole.py
    """

    from os import linesep as delimiter

    #__ON_KILLED = staticmethod(lambda: reactor.stop())

    #def __init__(self, killer=None):
    #    CmdOnlyBackend.__init__(self, killer or self.__ON_KILLED)

    def __init__(self, killer=None):
        self.backend = CmdOnlyBackend()

    def connectionMade(self):
        self.backend.connection_made()

    def lineReceived(self, line):
        try:
            self.backend.line_received(line)
        except StopIteration:
            reactor.stop()

cmd_backend_intro="""
This is a Backend to issue commands to Controller.

Type help on the prompt for help on available commands.

You might not see any output here - run output backend in another terminal.

Type <Ctrl-C> to finish (and kindly ignore the traceback which will follow.)
"""
def cmd_backend():
    """
    Interactive backend issuing commands to Controller.

    I do not want to stop reactor directly, but would like if it stopped if
    there are no more protocols.
    """
    backend = TwistedCmdBackend()
    # Start a LineReceiver on stdio:
    stdio.StandardIO(backend)
    # Start a default TCP client:
    start_backend(backend.backend)

def main():
    config.backend_conf(
            defaults={'NAME':'beah_cmd_backend'},
            overrides=config.backend_opts())
    log_handler()
    print cmd_backend_intro
    cmd_backend()
    reactor.run()

if __name__ == '__main__':
    main()
