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
from twisted.internet import reactor
from beah.wires.internals.twadaptors import ControllerAdaptor_Backend_JSON
from beah import config
from beah.misc import make_log_handler, str2log_level

import os
import sys
import logging

################################################################################
# FACTORY:
################################################################################
class BackendFactory(ReconnectingClientFactory):
    def __init__(self, backend, controller_protocol, byef=None):
        self.backend = backend
        self._done = False
        if not byef:
            def byef(evt):
                reactor.callLater(1, reactor.stop)
        def proc_evt_bye(evt):
            self._done = True
            if backend.controller:
                backend.controller.transport.loseConnection()
            byef(evt)
        backend.proc_evt_bye = proc_evt_bye
        self.controller_protocol = controller_protocol
        # set up ReconnectingClientFactory:
        # we do not want test killed by watchdog. repeat at least every 120s.
        self.maxDelay = 120

    def linfo(self, fmt, *args, **kwargs):
        l = [self.__class__.__name__]
        l.extend(args)
        logging.getLogger('backend').info('%s: '+fmt, *l, **kwargs)

    ########################################
    # INHERITED METHODS:
    ########################################
    def startedConnecting(self, connector):
        self.linfo('Started to connect.')

    def buildProtocol(self, addr):
        self.linfo('Connected.  Address: %r', addr)
        self.linfo('Resetting reconnection delay')
        self.resetDelay()
        controller = self.controller_protocol()
        controller.add_backend(self.backend)
        return controller

    def clientConnectionLost(self, connector, reason):
        self.linfo('Lost connection.  Reason: %s', reason)
        self.backend.set_controller()
        if not self._done:
            ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.linfo('Connection failed. Reason: %s', reason)
        self.backend.set_controller()
        if not self._done:
            ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def log_handler(log_file_name=None):
    conf = config.get_conf('beah-backend')
    if not log_file_name:
        if conf.has_option('DEFAULT', 'LOG_FILE'):
            log_file_name = conf.get('DEFAULT', 'LOG_FILE')
        else:
            log_file_name = conf.get('DEFAULT', 'NAME') + '.log'
    lp = conf.get('DEFAULT', 'LOG_PATH') or "/var/log"
    log = logging.getLogger('backend')
    cons = config.parse_bool(conf.get('DEFAULT', 'CONSOLE_LOG'))
    make_log_handler(log, lp, log_file_name, syslog=True, console=cons)
    return log

def start_backend(backend, host=None, port=None,
        adaptor=ControllerAdaptor_Backend_JSON,
        byef=None):
    conf = config.get_conf('beah-backend')
    host = host or conf.get('DEFAULT', 'INTERFACE')
    port = port or conf.get('DEFAULT', 'PORT')
    if os.name == 'posix':
        socket = conf.get('DEFAULT', 'SOCKET')
        # 0. check SOCKET_OPT (socket given on command line)
        if config.parse_bool(conf.get('DEFAULT', 'SOCKET_OPT')) and socket != '':
            port = ''
        # 1. check INTERFACE - if not empty nor localhost: must use TCP
        if host != '' and host != 'localhost':
            socket = ''
        # 2. check PORT_OPT (port given on command line)
        if config.parse_bool(conf.get('DEFAULT', 'PORT_OPT')) and port != '':
            socket = ''
    else:
        socket = ''
    logging.getLogger('backend').setLevel(str2log_level(conf.get('DEFAULT', 'LOG')))
    backend_factory = BackendFactory(backend, adaptor, byef)
    if socket != '':
        return reactor.connectUNIX(socket, backend_factory)
    elif port != '':
        return reactor.connectTCP(host, int(port), backend_factory)
    else:
        raise exceptions.Exception('Either socket or port must be configured.')

################################################################################
# TEST:
################################################################################
if __name__=='__main__':
    from beah.core.backends import PprintBackend
    from beah.core import command

    class DemoOutAdaptor(ControllerAdaptor_Backend_JSON):

        def linfo(self, fmt, *args, **kwargs):
            l = [self.__class__.__name__]
            l.extend(args)
            logging.getLogger('backend').info('%s: '+fmt, *l, **kwargs)

        def connectionMade(self):
            self.linfo("I am connected!")
            ControllerAdaptor_Backend_JSON.connectionMade(self)
            self.proc_cmd(self.backend, command.PING("Hello everybody!"))

        def connectionLost(self, reason):
            self.linfo("I was lost!")

        def lineReceived(self, data):
            self.linfo('Data received.  Data: %r', data)
            ControllerAdaptor_Backend_JSON.lineReceived(self, data)

    class DemoPprintBackend(PprintBackend):
        def set_controller(self, controller=None):
            PprintBackend.set_controller(self, controller)
            if controller:
                self.controller.proc_cmd(self, command.ping("Are you there?"))

    config.backend_conf(
            defaults={'NAME':'beah_demo_backend'},
            overrides=config.backend_opts())
    log_handler()
    start_backend(DemoPprintBackend(), adaptor=DemoOutAdaptor)
    reactor.run()

