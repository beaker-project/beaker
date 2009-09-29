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
from beah.wires.internals.twtask import Spawn
from beah.core.controller import Controller
from beah import config
from twisted.internet import protocol
from twisted.internet import reactor
import logging
import logging.handlers
import os
import sys

log = logging.getLogger('beacon')

class BackendListener(protocol.ServerFactory):
    def __init__(self, controller, backend_protocol=BackendAdaptor_JSON):
        self.protocol = backend_protocol or BackendAdaptor_JSON
        self.controller = controller

    def buildProtocol(self, addr):
        log.info('%s: Connected.  Address: %s', self.__class__.__name__, addr)
        backend = self.protocol()
        backend.set_controller(self.controller)
        return backend

class TaskListener(protocol.ServerFactory):
    def __init__(self, controller, task_protocol=TaskAdaptor_JSON):
        self.protocol = task_protocol or TaskAdaptor_JSON
        self.controller = controller

    def buildProtocol(self, addr):
        log.info('%s: Connected.  Address: %s', self.__class__.__name__, addr)
        task = self.protocol()
        task.set_controller(self.controller)
        return task

def start_server(conf=None, backend_host=None, backend_port=None,
        backend_adaptor=BackendAdaptor_JSON,
        task_host=None, task_port=None,
        task_adaptor=TaskAdaptor_JSON, spawn=None):

    # CONFIG:
    if not conf:
        conf = config.main_config()

    # LOGGING:
    log.setLevel(logging.WARNING if not config.parse_bool(conf.get('CONTROLLER', 'DEVEL')) else logging.DEBUG)

    # Create a directory for logging and check permissions
    lp = conf.get('CONTROLLER', 'LOG_PATH')
    if not os.access(lp, os.F_OK):
        try:
            os.makedirs(lp, mode=0755)
        except:
            print >> sys.stderr, "ERROR: Could not create %s." % lp
            # FIXME: should create a temp file
            raise
    elif not os.access(lp, os.X_OK | os.W_OK):
        print >> sys.stderr, "ERROR: Wrong access rights to %s." % lp
        # FIXME: should create a temp file
        raise

    lhandler = logging.handlers.RotatingFileHandler(conf.get('CONTROLLER', 'LOG_FILE_NAME'),
            maxBytes=1000000, backupCount=5)
    log.addHandler(lhandler)

    # RUN:
    backend_host = backend_host or conf.get('BACKEND', 'INTERFACE')
    backend_port = backend_port or int(conf.get('BACKEND', 'PORT'))
    task_host = task_host or conf.get('TASK', 'INTERFACE')
    task_port = task_port or int(conf.get('TASK', 'PORT'))
    spawn = spawn or Spawn(task_host, task_port)
    controller = Controller(spawn, on_killed=lambda: reactor.stop())
    def on_killed():
        if not controller.backends:
            reactor.stop()
            return
        reactor.callLater(2, reactor.stop)
    controller.on_killed = on_killed
    log.info("################################")
    log.info("#   Starting a Controller...   #")
    log.info("################################")
    log.info("Controller: BackendListener listening on %s:%s", backend_host,
            backend_port)
    reactor.listenTCP(backend_port,
            BackendListener(controller, backend_adaptor),
            interface=backend_host)
    log.info("Controller: TaskListener listening on %s:%s", task_host,
            task_port)
    reactor.listenTCP(task_port, TaskListener(controller, task_adaptor),
            interface=task_host)

if __name__ == '__main__':
    start_server()
    reactor.run()

