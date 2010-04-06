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
from twisted.internet.protocol import ProcessProtocol, ReconnectingClientFactory
from beah.wires.internals import twadaptors
from beah import config
from beah.misc import dict_update
import logging
import os

log = logging.getLogger('beah')

class TaskStdoutProtocol(ProcessProtocol):
    def __init__(self, task_id, task_protocol=twadaptors.TaskAdaptor_JSON):
        self.task_id = task_id
        self.task_protocol = task_protocol or twadaptors.TaskAdaptor_JSON
        self.task = None
        self.controller = None

    def connectionMade(self):
        log.info("%s:connectionMade", self.__class__.__name__)
        self.task = self.task_protocol()
        # FIXME: this is not very nice...
        self.task.send_cmd = lambda obj: self.transport.write(self.task.format(obj))
        self.task.task_id = self.task_id
        self.task.set_controller(self.controller)
        self.controller.task_started(self.task)

    def outReceived(self, data):
        self.task.dataReceived(data)

    def errReceived(self, data):
        self.task.lose_item(data)

    def processEnded(self, reason):
        log.info("%s:processEnded(%s)", self.__class__.__name__, reason)
        self.controller.task_finished(self.task, rc=reason.value.exitCode)
        self.task.set_controller()

def Spawn(host, port, proto=None, socket=''):
    def spawn(controller, backend, task_info, env, args):
        task_env = dict(env)
        # 1. set env.variables
        # BEAH_THOST - host name
        # BEAH_TPORT - port
        # BEAH_TSOCKET - socket
        # BEAH_TID - id of task - used to introduce itself when opening socket
        task_id = task_info['id']
        dict_update(task_env,
                CALLED_BY_BEAH="1",
                BEAH_THOST=str(host),
                BEAH_TPORT=str(port),
                BEAH_TSOCKET=str(socket),
                BEAH_TID=str(task_id),
                )
        ll = config.get_conf('beah').get('TASK', 'LOG')
        task_env.setdefault('BEAH_TASK_LOG', ll)
        val = os.getenv('PYTHONPATH')
        if val:
            task_env['PYTHONPATH'] = val
        # 2. spawn a task
        protocol = (proto or TaskStdoutProtocol)(task_id)
        protocol.controller = controller
        log.debug('spawn: Environment: %r.', task_env)
        reactor.spawnProcess(protocol, task_info['file'],
                args=[task_info['file']]+(args or []), env=task_env)
        # FIXME: send an answer to backend(?)
        return protocol.task_protocol
    return spawn

class TaskFactory(ReconnectingClientFactory):
    def __init__(self, task, controller_protocol):
        self.task = task
        self.controller_protocol = controller_protocol

    ########################################
    # INHERITED METHODS:
    ########################################
    def startedConnecting(self, connector):
        log.info('%s: Started to connect.', self.__class__.__name__)

    def buildProtocol(self, addr):
        log.info('%s: Connected.  Address: %s', self.__class__.__name__, addr)
        log.info('%s: Resetting reconnection delay', self.__class__.__name__)
        self.resetDelay()
        controller = self.controller_protocol()
        controller.add_task(self.task)
        return controller

    def clientConnectionLost(self, connector, reason):
        log.info('%s: Lost connection.  Reason:%s',
                self.__class__.__name__, reason)
        self.task.set_controller()
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.info('%s: Connection failed. Reason:%s', self.__class__.__name__,
                reason)
        self.task.set_controller()
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def start_task(conf, task, host=None, port=None,
        adaptor=twadaptors.ControllerAdaptor_Task_JSON, socket=None,
        ):
    factory = TaskFactory(task, adaptor)
    if os.name == 'posix':
        socket = socket or conf.get('TASK', 'SOCKET')
        if socket != '':
            return reactor.connectUNIX(socket, factory)
    host = host or conf.get('TASK', 'INTERFACE')
    port = port or int(conf.get('TASK', 'PORT'))
    if port != '':
        return reactor.connectTCP(host, int(port), factory)
    raise exceptions.Exception('Either socket or port must be given.')
