from beah.wires.internals.twbackend import start_backend, log_handler
from beah.core.backends import ExtBackend
from beah.core import command, event
from beah.core.constants import ECHO
from beah.misc.log_this import log_this
from beah.misc import localhost
from beah import config

from twisted.internet.defer import Deferred
from twisted.internet import reactor
import logging
import exceptions

conf = config.config()

log_handler('beah_forwarder_backend.log')
log = logging.getLogger('backend')

# FIXME: Use config option for log_on:
print_this = log_this(lambda s: log.debug(s), log_on=True)

class ForwarderBackend(ExtBackend):

    verbose_cls = False
    RETRY_IN = 10

    def __init__(self):
        self.__remotes = {}
        ExtBackend.__init__(self)

    def make_verbose(cls):
        if not cls.verbose_cls:
            cls.remote_backend = print_this(cls.remote_backend)
            cls.reconnect = print_this(cls.reconnect)
            cls.remote_call = print_this(cls.remote_call)
            cls.proc_evt_variable_get = print_this(cls.proc_evt_variable_get)
            cls.handle_evt_variable_get = print_this(cls.handle_evt_variable_get)
            cls.verbose_cls = True
    make_verbose = classmethod(make_verbose)

    def remote_backend(self, dest):
        dest_s = '%s:%s' % dest
        rb = self.__remotes.get(dest_s, None)
        if rb is None:
            rb = _RemoteBackend(self, dest)
            start_backend(rb, host=dest[0], port=dest[1])
            self.__remotes[dest_s] = rb
        return rb

    def reconnect(self, remote_be):
        rb = remote_be.clone()
        dest = rb.dest()
        dest_s = '%s:%s' % dest
        del remote_be
        del self.__remotes[dest_s]
        start_backend(rb, host=dest[0], port=dest[1])
        self.__remotes[dest_s] = rb

    def remote_call(self, cmd, host, port=None):
        if port is None:
            port = conf.get('BACKEND', 'PORT')
        port = int(port)
        # create a backend if necessary
        rem = self.remote_backend((host, port))
        return rem.send_cmd(cmd)

    def handle_evt_variable_get(self, result, evt):
        type, pass_, remote_be, cmd_id, rest = result
        if type == 'timeout':
            log.error("Timeout.")
            remote_be.done(cmd_id)
            reactor.callLater(self.RETRY_IN, self.proc_evt_variable_get, evt)
            return
        if type == 'forward_response' and pass_ and rest.command() == 'variable_value':
            self.controller.proc_cmd(self, rest)
            remote_be.done(cmd_id)
            return
        if type != 'echo':
            log.warning("Unexpected answer. Waiting more... (diagnostic=%r)", result)
            remote_be.more(cmd_id).addCallback(self.handle_evt_variable_get, evt)
            return
        log.error("Remote end send echo without any answer! (diagnostic=%r)", result)
        remote_be.done(cmd_id)
        reactor.callLater(self.RETRY_IN, self.proc_evt_variable_get, evt)

    def proc_evt_variable_get(self, evt):
        # FIXME!20100129 is this necessary?
        #if not isinstance(evt, event.Event):
        #    evt = event.Event(evt)
        host = evt.arg('dest')
        # FIXME: local host with different port # could be used! (for
        # testing multihost on single machine)
        if localhost(host):
            return
        # loop for testing:
        if host == 'test.loop':
            host = 'localhost'
            # Clean the dest field to avoid inifinite loop:
            evt.args()['dest'] = ''
        # FIXME!!! remote Controller could listen on another port:
        port = conf.get('BACKEND', 'PORT')
        cmd = command.forward(event=evt, host=host, port=port)
        d = self.remote_call(cmd, host, port)
        if d:
            d.addCallback(self.handle_evt_variable_get, evt)

class _RemoteBackend(ExtBackend):

    """
    Backend interacting with remote Controller.
    """

    ALLOWED_COMMANDS = ['variable_value']
    TIMEOUT = 5

    _CONNECTED=object()
    _NEW=object()
    _IDLE=object()

    def __init__(self, caller, dest, queue=None, pending=None):
        self.__caller = caller
        self.__dest = dest
        self.__queue = queue or []
        self.__pending = pending or {}
        self.__status = self._NEW
        ExtBackend.__init__(self)

    verbose_cls = False

    def make_verbose(cls):
        if not cls.verbose_cls:
            cls.send_cmd = print_this(cls.send_cmd)
            cls.done = print_this(cls.done)
            cls.more = print_this(cls.more)
            cls.set_controller = print_this(cls.set_controller)
            cls.clone = print_this(cls.clone)
            cls.proc_evt_forward_response = print_this(cls.proc_evt_forward_response)
            cls.proc_evt_echo = print_this(cls.proc_evt_echo)
            cls.verbose_cls = True
    make_verbose = classmethod(make_verbose)

    def dest(self):
        return self.__dest

    def send_cmd(self, cmd):
        for c, _ in self.__pending.values():
            if cmd.same_as(c):
                return None
        d = Deferred()
        cid = cmd.id()
        self.__queue.append(cid)
        self.__pending[cid] = (cmd, d)
        if self.__status is self._CONNECTED:
            self.controller.proc_cmd(self, cmd)
            reactor.callLater(self.TIMEOUT, self.timeout, cid)
        return d

    def __replaced(self, cmd_id, d):
        c, dd = self.__pending.get(cmd_id, (None, None))
        if c is None:
            return None
        self.__pending[cmd_id] = (c, d)
        return dd

    def timeout(self, cmd_id):
        d = self.__replaced(cmd_id, None)
        if d:
            d.callback(('timeout', False, self, cmd_id, None))

    def more(self, cmd_id):
        d = Deferred()
        if self.__replaced(cmd_id, d):
            raise exceptions.RuntimeError('more should be called from callbacks only!')
        return d

    def done(self, cmd_id):
        if self.__pending[cmd_id][1]:
            raise exceptions.RuntimeError('done should be called from callbacks only!')
        del self.__pending[cmd_id]
        self.__queue = list([cid for cid in self.__queue if cid != cmd_id])

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        if controller:
            self.__status = self._CONNECTED
            # FIXME: implement proper output filterring instead of no_output:
            controller.proc_cmd(self, command.no_output())
            for cid in self.__queue:
                cmd, d = self.__pending[cid]
                controller.proc_cmd(self, cmd)
                reactor.callLater(self.TIMEOUT, self.timeout, cid)
        else:
            self.__status = self._IDLE

    def clone(self):
        return _RemoteBackend(self.__caller, self.__dest, self.__queue,
                self.__pending)

    def proc_evt_forward_response(self, evt):
        cmd = command.command(evt.arg('command'))
        cid = evt.arg('forward_id')
        d = self.__replaced(cid, None)
        if d:
            cmd_ok = cmd.command() in self.ALLOWED_COMMANDS
            if not cmd_ok:
                log.warning("Command %s not allowed! cmd=%r", cmd.command(), cmd)
            d.callback(('forward_response', cmd_ok, self, cid, cmd))

    def proc_evt_echo(self, evt):
        cid = evt.arg('cmd_id')
        d = self.__replaced(cid, None)
        if d:
            d.callback(('echo', evt.arg('rc') == ECHO.OK, self, cid, evt))

def start_forwarder_backend():
    if config.parse_bool(conf.get('BACKEND', 'DEVEL')):
        ForwarderBackend.make_verbose()
        _RemoteBackend.make_verbose()
    backend = ForwarderBackend()
    # Start a default TCP client:
    start_backend(backend, byef=lambda evt: reactor.callLater(1, reactor.stop))
    return backend

def main():
    start_forwarder_backend()
    reactor.run()

if __name__ == '__main__':
    from beah.bin.srv import main_srv
    from beah.core import event
    srv = main_srv()

    class FakeTask(object):
        origin = {'signature':'FakeTask'}
        task_id = 'no-id'
        def proc_cmd(self, cmd):
            log.debug("FakeTask.proc_cmd(%r)", cmd)
    t = FakeTask()
    reactor.callLater(2, srv.proc_evt, t, event.variable_set('say_hi', 'Hello World!'))
    #reactor.callLater(2.1, srv.proc_evt, t, event.variable_get('say_hi'))
    reactor.callLater(2.2, srv.proc_evt, t, event.variable_get('say_hi', dest='test.loop'))

    class FakeBackend(object):
        def proc_evt(self, evt, **kwargs):
            log.debug("FakeBackend.proc_evt(%r, **%r)", evt, kwargs)
    b = FakeBackend()
    reactor.callLater(3, srv.proc_cmd, b, command.kill())

    main()

