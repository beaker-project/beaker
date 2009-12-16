from beah.wires.internals.twbackend import start_backend, log_handler
from beah.core.backends import ExtBackend
from beah.core import command
from beah.misc.log_this import log_this
from beah.misc import localhost
from beah import config

from twisted.internet import reactor
import logging

conf = config.config()

log_handler('beah_forwarder_backend.log')
log = logging.getLogger('backend')

# FIXME: Use config option for log_on:
print_this = log_this(lambda s: log.debug(s), log_on=True)

class ForwarderBackend(ExtBackend):

    verbose_cls = False

    def __init__(self):
        self.__remotes = {}

    def make_verbose(cls):
        if not cls.verbose_cls:
            cls.remote_backend = print_this(cls.remote_backend)
            cls.reconnect = print_this(cls.reconnect)
            cls.remote_call = print_this(cls.remote_call)
            cls.proc_evt_variable_get = print_this(cls.proc_evt_variable_get)
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
        rem.send_cmd(cmd)

    def proc_evt_variable_get(self, evt):
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
        # FIXME: remote Controller could listen on another port:
        port = conf.get('BACKEND', 'PORT')
        self.remote_call(
                command.forward(event=evt, host=host, port=port),
                host, port)

class _RemoteBackend(ExtBackend):

    """
    Backend interacting with remote Controller.
    """

    ALLOWED_COMMANDS = ['variable_value']

    _CONNECTED=()
    _NEW=()
    _IDLE=()

    def __init__(self, caller, dest, queue=None):
        self.__caller = caller
        self.__dest = dest
        self.__queue = queue or []
        self.__status = self._NEW

    verbose_cls = False

    def make_verbose(cls):
        if not cls.verbose_cls:
            cls.send_cmd = print_this(cls.send_cmd)
            cls.done = print_this(cls.done)
            cls.set_controller = print_this(cls.set_controller)
            cls.clone = print_this(cls.clone)
            cls.proc_evt_forward_response = print_this(cls.proc_evt_forward_response)
            cls.proc_evt_echo = print_this(cls.proc_evt_echo)
            cls.verbose_cls = True
    make_verbose = classmethod(make_verbose)

    def dest(self):
        return self.__dest

    def send_cmd(self, cmd):
        self.__queue.append(cmd)
        if self.__status is self._CONNECTED:
            self.controller.proc_cmd(self, cmd)

    def done(self, remote_be, cmd_id, evt):
        n = len(self.__queue)
        while n>0:
            n -= 1
            cmd = self.__queue[n]
            if cmd.id() == cmd_id:
                del self.__queue[n]

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        if controller:
            self.__status = self._CONNECTED
            # FIXME: implement proper output filterring instead of no_output:
            controller.proc_cmd(self, command.no_output())
            for cmd in self.__queue:
                controller.proc_cmd(self, cmd)
        else:
            self.__status = self._IDLE
            reactor.callLater(10, self.__caller.reconnect, self)

    def clone(self, remote_be):
        return _RemoteBackend(self.__caller, self.__dest, self.__queue)

    def proc_evt_forward_response(self, evt):
        cmd = command.command(evt.arg('command'))
        if cmd.command() in self.ALLOWED_COMMANDS:
            self.__caller.controller.proc_cmd(self.__caller, cmd)
        else:
            log.warning("Command %s not allowed! cmd=%r", cmd.command(), cmd)
            pass

    def proc_evt_echo(self, evt):
        self.done(self, evt.arg('cmd_id'), evt)

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
        task_info = {'task':'fake', 'id':'no_id'}
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

