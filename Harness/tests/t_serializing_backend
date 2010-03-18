#!/usr/bin/python

from beah.core.backends import SerializingBackend
from beah.core import event
from beah.misc.log_this import print_this
from twisted.internet import reactor
import sys
import traceback

if __name__ == '__main__':
    def test_serializing_backend():
        sbe = SerializingBackend()

        @print_this
        def proc_pong(sbe):
            @print_this
            def proc_pong_done(evt):
                print "DONE: ", evt
                sys.stdout.flush()
                sbe.set_idle()
            @print_this
            def proc_pong_(evt):
                sbe.set_busy()
                delay = evt.arg('delay', 1)
                print "START: ", evt
                print "waiting for %s seconds." % delay
                sys.stdout.flush()
                reactor.callLater(delay, proc_pong_done, evt)
            return proc_pong_
        sbe.proc_evt_pong = proc_pong(sbe)

        @print_this
        def proc_bye(evt):
            reactor.callLater(1, reactor.stop)
            print "proc_bye: stopping in 1 second."
            sys.stdout.flush()
        sbe.proc_evt_bye = proc_bye

        @print_this
        def proc_error(evt):
            print "proc_error(%r)" % evt
            traceback.print_exc()
        sbe.proc_error = proc_error

        sbe.proc_evt(event.Event('pong', message="Hi!", delay=5))
        sbe.proc_evt(event.Event('pong', message="Are you there?", delay=2))
        sbe.proc_evt(event.Event('pong', message="I am leaving!", delay=2))
        sbe.proc_evt(event.Event('pong', message="Really..."))
        sbe.proc_evt(event.Event('bye'))

    reactor.callWhenRunning(test_serializing_backend)
    reactor.run()
