import sys
import exceptions
from optparse import OptionParser
from random import randint

from twisted.internet import protocol
from twisted.internet import reactor

from beah.core import event, command
from beah.core.constants import ECHO
from beah.wires.internals.twmisc import JSONProtocol

class ExampleController(JSONProtocol):

    """
    Example FakeController
    """

    def proc_input(self, cmd):
        """Implement this. Use self.send_cmd(evt) to answer."""
        print "%s.proc_input(%r)" % (self, cmd)
        cmd = command.Command(cmd)
        if cmd.command() == 'ping':
            evt = event.Event('pong')
            self.send_cmd(evt)

    def send_cmd(self, evt):
        print "%s.send_cmd(%s)" % (self, evt)
        return JSONProtocol.send_cmd(self, evt)

    def connectionMade(self):
        print "%s.connectionMade()" % (self,)

    def connectionLost(self, reason):
        print "%s.connectionLost(%s)" % (self, reason)

class IgnorantController(ExampleController):

    def proc_input(self, cmd):
        print "%s.send_cmd(%s)" % (self, cmd)

class EchoController(ExampleController):

    def origin(self):
        return {"from": self.__class__.__name__}

    def proc_input(self, cmd):
        """Implement this. Use self.send_cmd(evt) to answer."""
        print "%s.proc_input(%r)" % (self, cmd)
        self.proc_cmd(command.Command(cmd))

    def proc_def_handler(self, cmd, echo_evt):
        print "%s.proc_def_handler(%r, ...)" % (self, cmd)
        return echo_evt

    def proc_exception(self, cmd, echo_evt):
        print "%s.proc_exception(%r, ...)" % (self, cmd)
        return echo_evt

    def proc_cmd(self, cmd):
        """
        Process received Command.

        @cmd is a command. Should be an instance of Command class.
        """
        print "%s.proc_cmd(%r)" % (self, cmd)
        handler = getattr(self, "proc_cmd_"+cmd.command(), None)
        if not handler:
            echo_evt = self.proc_def_handler(cmd, event.echo(cmd,
                ECHO.NOT_IMPLEMENTED, origin=self.origin()))
        else:
            try:
                echo_evt = handler(cmd, event.echo(cmd, ECHO.OK,
                    origin=self.origin()))
            except:
                echo_evt = proc_exception(cmd, event.echo(cmd, ECHO.EXCEPTION,
                    origin=self.origin(), exception=format_exc()))
        if echo_evt:
            self.send_cmd(echo_evt)

class VarGetController(EchoController):

    def proc_cmd_forward(self, cmd, echo_evt):
        evt = event.event(cmd.arg('event'))
        evev = evt.event()
        if evev not in ['variable_get', 'variable_set']:
            return echo_evt
        new_cmd = self.proc_evt(evt)
        if new_cmd:
            self.send_cmd(event.forward_response(new_cmd, cmd.id()))
        else:
            echo_evt = event.echo(cmd, ECHO.EXCEPTION, origin=self.origin(),
                    exception='No forward_response.')
        return echo_evt

    def set_var(self, key, handle, dest, value):
        pass

    def get_var(self, key, handle, dest):
        return "SomeValue"

    def proc_evt(self, evt):
        evev = evt.event()
        if evev in ['variable_set', 'variable_get']:
            handle = evt.arg('handle', '')
            dest = evt.arg('dest', '')
            key = evt.arg('key')
            if evev == 'variable_set':
                self.set_var(key, handle, dest, evt.arg('value'))
            else:
                value = self.get_var(key, handle, dest)
                return command.variable_value(key, value, handle=handle,
                        dest=dest)

def make_slow(c, lower=5, upper=15):
    c_proc_cmd = c.proc_cmd
    if upper <= lower:
        upper = lower + 1
    def proc_cmd(cmd):
        reactor.callLater(randint(lower, upper), c_proc_cmd, cmd)
    c.proc_cmd = proc_cmd

def start_server(port, proto, host=''):
    listener = protocol.ServerFactory()
    listener.protocol = proto
    reactor.listenTCP(port, listener, interface=host)

def conf_opt(args):
    """
    Parses command line for common options.

    This seeks only the few most common options. For other options use your own
    parser.

    Returns tuple (options, args). For descritpin see
    optparse.OptionParser.parse_args and optparse.Values
    """
    opt = OptionParser()
    opt.add_option("-v", "--verbose", action="count", dest="verbose",
            help="Increase verbosity.")
    opt.add_option("-q", "--quiet", action="count", dest="quiet",
            help="Decrease verbosity.")
    opt.add_option("-p", "--port", action="store", dest="port",
            help="Port to listen on.")
    opt.add_option("-s", "--slow", action="store_true", dest="slow",
            help="Create rather slow controller.")
    return opt.parse_args(args)

def conf_main(conf, args):
    (opts, rest) = conf_opt(args)
    if opts.verbose is not None or opts.quiet is not None:
        conf['verbosity'] = (opts.verbose or 0) - (opts.quiet or 0)
    else:
        conf['verbosity'] = 0
    conf['port'] = int(opts.port or 12432)
    conf['slow'] = opts.slow
    return conf, rest

def make_controller(args, slow=False):
    if not args:
        raise exceptions.RuntimeError("missing controller type.")
    if args[0]=='help':
        raise exceptions.NotImplementedError
    if args[0]=='echo':
        if slow:
            def make_controller_():
                c = EchoController()
                make_slow(c)
                return c
            return make_controller_
        else:
            return EchoController
    if args[0]=='ignorant':
        return IgnorantController
    if args[0]=='var_const':
        def get_var(key, handle, dest): return args[1]
        def make_controller_():
            c = VarGetController()
            c.get_var = get_var
            if slow:
                make_slow(c)
            return c
        return make_controller_
    raise exceptions.RuntimeError("unrecognized controller '%s'" % args[0])

def main():
    conf, rest = conf_main({}, sys.argv[1:])
    start_server(conf['port'], make_controller(rest, slow=conf['slow']))
    reactor.run()

if __name__ == '__main__':
    main()

