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

from beah.wires.internals.twadaptors import BackendAdaptor_JSON, TaskAdaptor_JSON

from twisted.internet import protocol

import logging
log = logging.getLogger('beacon')

class BackendListener(protocol.ServerFactory):
    def __init__(self, controller, backend_protocol=BackendAdaptor_JSON):
        self.protocol = backend_protocol or BackendAdaptor_JSON
        self.controller = controller

    def buildProtocol(self, addr):
        print self.__class__.__name__, ': Connected.  Address: %r' % addr
        backend = self.protocol()
        backend.set_controller(self.controller)
        return backend

class TaskListener(protocol.ServerFactory):
    def __init__(self, controller, task_protocol=TaskAdaptor_JSON):
        self.protocol = task_protocol or TaskAdaptor_JSON
        self.controller = controller

    def buildProtocol(self, addr):
        print self.__class__.__name__, ': Connected.  Address: %r' % addr
        task = self.protocol()
        task.set_controller(self.controller)
        return task

from twisted.internet import reactor
def start_server(config=None, backend_host=None, backend_port=None,
        backend_adaptor=BackendAdaptor_JSON,
        task_host=None, task_port=None,
        task_adaptor=TaskAdaptor_JSON, spawn=None):
    # CONFIG:
    if not config:
        from beah import config
        config.config(DEVEL=lambda: True, SRV_LOG=lambda: True)
        #print dir(config)

    # LOGGING:
    import logging
    log.setLevel(logging.WARNING if not config.DEVEL() else logging.DEBUG)

    # Create a directory for logging and check permissions
    import os
    try:
        if not os.access(config.LOG_PATH(), os.F_OK):
            try:
                os.makedirs(config.LOG_PATH(), mode=0755)
            except:
                print "WARNING: Could not create %s." % config.LOG_PATH()
                # FIXME: should create a temp file
                raise
        elif not os.access(config.LOG_PATH(), os.X_OK | os.W_OK):
            print "WARNING: Wrong access rights to %s." % config.LOG_PATH()
            # FIXME: should create a temp file
            raise
    finally:
        del os

    import logging.handlers
    lhandler = logging.handlers.RotatingFileHandler(config.LOG_FILE_NAME(),
            maxBytes=100000, backupCount=5)
    log.addHandler(lhandler)

    # RUN:
    backend_host = backend_host or config.HOST()
    backend_port = backend_port or config.PORT()
    task_host = task_host or config.THOST()
    task_port = task_port or config.TPORT()
    from beah.wires.internals.twtask import Spawn
    spawn = spawn or Spawn(task_host, task_port)
    from beah.core.controller import Controller
    controller = Controller(spawn, on_killed=lambda: reactor.stop())
    def on_killed():
        if not controller.backends:
            reactor.stop()
            return
        reactor.callLater(2, reactor.stop)
    controller.on_killed = on_killed
    reactor.listenTCP(backend_port,
            BackendListener(controller, backend_adaptor),
            interface=backend_host)
    reactor.listenTCP(task_port, TaskListener(controller, task_adaptor),
            interface=task_host)

if __name__ == '__main__':
    start_server()
    reactor.run()

