from beah.wires.internals.twbackend import start_backend
from beah.core import command
from beah.core.backends import ExtBackend
from beah.core.constants import ECHO
from twisted.internet import reactor
import pprint
import exceptions

class Wait(object): pass
WAIT = Wait()

class BeahRunner(ExtBackend):
    def __init__(self, coro):
        self.__coro = coro
        self.__monitor = None
        self.__wait = None
        self.__cmd = None

    def dbg(self, msg=None):
        if msg:
            print "*** Msg:", msg
        if self.__cmd:
            print "*** Cmd:", self.__cmd
        if self.__wait or self.__monitor:
            print "*** Wait:", self.__wait, " for:", self.__monitor

    def do_beah_cmd(self):
        #self.dbg("do_beah_cmd called")

        if self.__wait:
            return

        while True:
            try:
                try:
                    next_cmd = self.__coro.next()
                    #self.dbg("coro.next() -> %r" % next_cmd)
                except exceptions.StopIteration:
                    print "\n========================================\nDone!\n========================================"
                    reactor.stop()
                    break

                if next_cmd is WAIT:
                    if self.__monitor:
                        self.__wait = True
                        print "\n========================================\nWAITING!"
                        break
                    continue

                if not isinstance(next_cmd, command.Command):
                    self.__monitor = next_cmd
                    print "\n========================================\nMonitoring:", next_cmd
                    continue

                self.__cmd = next_cmd
                print "\n========================================\nCommand: ",
                pprint.pprint(next_cmd)
                print "----------------------------------------"
                self.controller.proc_cmd(self, next_cmd)
            except:
                reactor.stop()
                raise

    def set_controller(self, controller=None):
        ExtBackend.set_controller(self, controller)
        if controller:
            self.do_beah_cmd()
        #else:
        #    reactor.stop()

    def pre_proc(self, evt):
        pprint.pprint(evt)

        if self.__monitor:
            if callable(self.__monitor):
                if self.__monitor(evt):
                    print "\n========================================\nFound!"
                    self.__monitor = None
                    self.__wait = None
                    self.do_beah_cmd()
                return False
            if evt.event() == self.__monitor:
                print "\n========================================\nFound!"
                self.__monitor = None
                self.__wait = None
                self.do_beah_cmd()
        return False

    def proc_evt_echo(self, evt):
        if evt.arg('cmd_id', '') == self.__cmd.id():
            if evt.args()['rc'] == ECHO.OK:
                self.do_beah_cmd()
                return
            if evt.args()['rc'] == ECHO.NOT_IMPLEMENTED:
                print "--- ERROR: Command is not implemented."
                reactor.stop()
                return
            if evt.args()['rc'] == ECHO.EXCEPTION:
                print "--- ERROR: Command raised an exception."
                print evt.args()['exception']
                reactor.stop()
                return


def beah_run(coro):
    """\
This is a Backend to issue script to Controller.

Type help on the prompt for help o commands.

You might not see any output here - run out_backend.

Known issues:

 * Type <Ctrl-C> to finish.

   I do not want to stop reactor directly, but would like if it stopped when
   there are no more protocols.
"""
    backend = BeahRunner(coro)
    # Start a default TCP client:
    start_backend(backend)

if __name__ == '__main__':
    def coro():
        yield command.ping('Are you there?')
        yield command.PING('Hello World!')
        yield command.command('dump')
        yield command.run('/usr/bin/bash', args=['-c','echo $ZZ1; echo $ZZ2'], env=dict(ZZ1='Zzzz...', ZZ2='__ZZZZ__'))
        yield 'end' # start monitoring 'end'
        yield command.command('dump')
        yield WAIT
        yield command.command('dump')
        return

    beah_run(coro())
    print "\n********************\n%s\n********************" % "Starting reactor."
    try:
        try:
            reactor.run()
        finally:
            print "\n********************\n%s\n********************" % "Reactor stopped!"
    except:
        raise

