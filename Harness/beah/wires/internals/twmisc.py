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

import simplejson as json
from twisted.protocols import basic
from exceptions import NotImplementedError

class JSONProtocol(basic.LineReceiver):
    """Protocol to send and receive new-line delimited JSON objects"""
    delimiter = "\n"

    ########################################
    # METHODS TO REIMPLEMENT:
    ########################################
    def proc_input(self, cmd):
        """Process object received in a message"""
        raise NotImplementedError

    def lose_item(self, data):
        raise

    ########################################
    # OWN METHODS:
    ########################################
    def send_cmd(self, obj):
        """Send an object as a message"""
        self.transport.write(self.format(obj))

    def format(obj):
        """Create a message from an object"""
        return json.dumps(obj) + "\n"
    # AVOID DECORATORS - KEEP PYTHON 2.2 COMPATIBILITY
    format = staticmethod(format)

    ########################################
    # INHERITED METHODS:
    ########################################
    def lineReceived(self, data):
        try:
            obj = json.loads(data)
        except:
            obj = self.lose_item(data)
        self.proc_input(obj)

import os
from twisted.internet import abstract
from twisted.internet.error import ConnectionDone
class OsFifo(abstract.FileDescriptor):
    def __init__(self, reactor, fifo_name, protocol, keep_alive=False):
        abstract.FileDescriptor.__init__(self, reactor)
        self.keep_alive = keep_alive
        self.fd = os.open(fifo_name, os.O_NONBLOCK | os.O_RDONLY)
        self.protocol = protocol
        self.protocol.makeConnection(self)

    def doRead(self):
        data = os.read(self.fd, 4096)
        if data:
            self.protocol.dataReceived(data)
        elif not self.keep_alive:
            self.connectionLost(ConnectionDone)

    def connectionLost(self, reason=ConnectionDone):
        self.stopReading()
        os.close(self.fd)
        self.protocol.connectionLost(reason)

    def fileno(self):
        return self.fd

