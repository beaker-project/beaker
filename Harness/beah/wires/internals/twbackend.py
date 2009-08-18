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

from twisted.internet.protocol import ReconnectingClientFactory

################################################################################
# FACTORY:
################################################################################
class BackendFactory(ReconnectingClientFactory):
    def __init__(self, backend, controller_protocol, byef=None):
        self.backend = backend
        if byef:
            self.backend.proc_evt_bye = byef
        self.controller_protocol = controller_protocol

    ########################################
    # INHERITED METHODS:
    ########################################
    def startedConnecting(self, connector):
        print self.__class__.__name__, ': Started to connect.'

    def buildProtocol(self, addr):
        print self.__class__.__name__, ': Connected.  Address: %r' % addr
        print self.__class__.__name__, ': Resetting reconnection delay'
        self.resetDelay()
        controller = self.controller_protocol()
        controller.add_backend(self.backend)
        return controller

    def clientConnectionLost(self, connector, reason):
        print self.__class__.__name__, ': Lost connection.  Reason:', reason
        self.backend.set_controller()
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print self.__class__.__name__, ': Connection failed. Reason:', reason
        self.backend.set_controller()
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

from twisted.internet import reactor
from beah.wires.internals.twadaptors import ControllerAdaptor_Backend_JSON
from beah import config
config.config()
def start_backend(backend, host=None, port=None,
        adaptor=ControllerAdaptor_Backend_JSON,
        byef=None):
    host = host or config.HOST()
    port = port or config.PORT()
    reactor.connectTCP(host, port, BackendFactory(backend, adaptor, byef))

################################################################################
# TEST:
################################################################################
if __name__=='__main__':
    from beah.core.backends import PprintBackend
    from beah.core import command

    class DemoOutAdaptor(ControllerAdaptor_Backend_JSON):
        def connectionMade(self):
            print "%s: I am connected!" % self.__class__.__name__
            ControllerAdaptor_Backend_JSON.connectionMade(self)
            self.proc_cmd(self.backend, command.PING("Hello everybody!"))

        def connectionLost(self, reason):
            print "%s: I was lost!" % self.__class__.__name__

        def lineReceived(self, data):
            print 'Data received.  Data: %r' % data
            ControllerAdaptor_Backend_JSON.lineReceived(self, data)

    class DemoPprintBackend(PprintBackend):
        def set_controller(self, controller=None):
            PprintBackend.set_controller(self, controller)
            if controller:
                self.controller.proc_cmd(self, command.ping("Are you there?"))

    start_backend(DemoPprintBackend(), adaptor=DemoOutAdaptor, byef=lambda evt: reactor.stop())
    reactor.run()

