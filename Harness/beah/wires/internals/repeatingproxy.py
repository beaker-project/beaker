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

"""
Module to handle network failures when using XML-RPC.

CLASSES:

RepeatingProxy(twisted.web.xmlrpc.Proxy):
    handle network failures by auto-retrying after defined sublcass of
    failures.

"""

from twisted.internet import reactor
from twisted.web.xmlrpc import Proxy
from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectionRefusedError
from beah.misc.log_this import print_this
from beah.misc import make_class_verbose

import sys

class RepeatingProxy(Proxy):

    """
    Repeat XML-RPC until it is delivered.

    Set delay for retry timer and max_retries for maximal number of retries for
    individual calls.

    is_auto_retry_condition and is_accepted_failure are used to decide on
    action.

    Therte are two modes of operation: parallel and serializing.

    In parallel mode, submitted calls are processed in parallel: remote calls
    are considered independent, and when one fails it does not affect other
    already submitted calls.

    In serializing mode, submitted calls are cached, and are processed in
    order, later call waiting for previous to finish.

    This implementation will retry forever on ConnectionRefusedError.

    There are two ways how to handle idle status:
    * by overriding on_idle
    * by calling when_idle which returns deferred (which is default on_idle's
      behavior.)
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize instance varziables and pass all arguments to the base class.
        """
        # __cache: internal storage for pending remote calls and associated
        # deferreds
        self.__cache = []
        # __sleep: True when waiting for remore call to complete
        self.__sleep = False
        # __pending: number of pending requests
        self.__pending = 0
        # __on_idle: deferred which will be called when there are no more calls
        self.__on_idle = None
        # delay: number of seconds to wait before retrying
        self.delay = 60
        self.max_retries = None
        # serializing: allow only one pending remote call when True
        self.serializing = False
        Proxy.__init__(self, *args, **kwargs)

    def on_idle(self):
        if self.__on_idle is not None:
            d = self.__on_idle
            self.__on_idle = None
            d.callback(True)

    def when_idle(self):
        self.__on_idle = Deferred()
        return self.__on_idle

    def dump(self):
        return "%r %r" % (self,
                dict(cache=self.__cache, sleep=self.__sleep,
                    pending=self.__pending))

    def is_auto_retry_condition(self, fail):
        """
        Failures which are handled by retry unconditionally.

        When True is returned the call is rescheduled.
        """
        return fail.check(ConnectionRefusedError)

    def is_accepted_failure(self, fail):
        """
        Accepted failures.

        When this method returns True, failure will be propagated to original
        deferred errback, otherwise will be retried.

        Example:
            return not fail.check(ConnectionRefusedError)
        """
        return True

    def on_ok(self, result, d):
        """
        Handler for successfull remote call.
        """
        self.__pending -= 1
        self.__sleep = False
        d.callback(result)
        self.send_next()

    def on_error(self, fail, m):
        """
        Handler for unsuccessfull remote call.
        """
        self.__pending -= 1
        if not self.is_auto_retry_condition(fail):
            if m[1] is None:
                count = 1
            else:
                m[1] -= 1
                count = m[1]
            if count <= 0 or self.is_accepted_failure(fail):
                self.__sleep = False
                m[0].errback(fail)
                self.send_next()
                return
        if self.serializing:
            self.insert(m)
        else:
            self.push(m)
        reactor.callLater(self.delay, self.resend)
        self.__sleep = True

    def resend(self):
        """
        Retry call after timeout.
        """
        self.__sleep = False
        self.send_next()

    def send_next(self):
        """
        Process next from queue.
        """
        if self.is_idle():
            self.on_idle()
            return False
        if self.is_empty() or self.__sleep:
            return False
        if self.serializing and self.__pending > 0:
            self.__sleep = True
            return False
        [d, count, method, args, kwargs] = m = self.pop()
        if self.serializing:
            self.__sleep = True
        self.callRemote_(method, *args, **kwargs) \
                .addCallbacks(self.on_ok, self.on_error, callbackArgs=[d],
                        errbackArgs=[m])
        return True

    def callRemote_(self, method, *args, **kwargs):
        """
        Method to call superclass' callRemote
        """
        answ = Proxy.callRemote(self, method, *args, **kwargs)
        self.__pending += 1
        return answ

    def callRemote(self, method, *args, **kwargs):
        """
        Overridden base class method, to handle retrying.
        """
        # Method has to return new deferred, as the original one will be
        # consumed internally.
        d = Deferred()
        self.push([d, self.max_retries, method, args, kwargs])
        self.send_next()
        return d

    def is_idle(self):
        return self.__pending == 0 and self.is_empty()

    def is_empty(self):
        return not self.__cache

    def pop(self):
        return self.__cache.pop(0)

    def insert(self, m):
        self.__cache.insert(0, m)

    def push(self, m):
        self.__cache.append(m)

    _VERBOSE = ('callRemote', 'callRemote_')
    _MORE_VERBOSE = ('is_auto_retry_condition', 'is_accepted_failure', 'on_ok', 'on_error',
                'resend', 'send_next', 'when_idle', 'is_empty', 'is_idle',
                'pop', 'insert', 'push')

if __name__ == '__main__':

    import exceptions
    import xmlrpclib
    from twisted.web.xmlrpc import XMLRPC
    from twisted.web import server

    def chk(result, method, result_ok, expected_ok):
        print "%s: method %s resulted in %s %s%s" % (
                result_ok == expected_ok and "OK" or "ERROR",
                method,
                result_ok == expected_ok and "expected" or "unexpected",
                result_ok and "pass" or "failure",
                '', #":\n%s" % result,
                )
        return None
    chk = print_this(chk)

    def rem_call(proxy, method, exp_):
        return proxy.callRemote(method) \
                .addCallbacks(chk, chk,
                        callbackArgs=[method, True, exp_],
                        errbackArgs=[method, False, exp_])
    rem_call = print_this(rem_call)

    class TestHandler(XMLRPC):
        _VERBOSE = ('xmlrpc_test', 'xmlrpc_test_exc', 'xmlrpc_test_exc2')
        def xmlrpc_test(self): return "OK"
        def xmlrpc_test_exc(self): raise exceptions.RuntimeError
        def xmlrpc_test_exc2(self): raise exceptions.NotImplementedError

    make_class_verbose(RepeatingProxy, print_this)
    make_class_verbose(TestHandler, print_this)
    p = RepeatingProxy(url='http://localhost:54123/')
    #def accepted_failure(fail):
    #    if fail.check(exceptions.NotImplementedError):
    #        # This does not work :-(
    #        return True
    #    if fail.check(xmlrpclib.Fault):
    #        # This would work:
    #        return True
    #    return False
    #accepted_failure = print_this(accepted_failure)
    #p.is_accepted_failure = accepted_failure
    p.delay = 3
    p.max_retries = 6
    print 80*"="
    print "Serializing RepeatingProxy:"
    print 80*"="
    p.serializing = True
    def run_again(result):
        print 80*"="
        print "Not serializing RepeatingProxy:"
        print 80*"="
        p.serializing = False
        p.when_idle().addCallback(stopper(1))
        rem_call(p, 'test', True)
        rem_call(p, 'test2', False)
        rem_call(p, 'test_exc', False)
        rem_call(p, 'test_exc2', False)
    def stopper(delay=1):
        def cb(result):
            reactor.callLater(delay, reactor.stop)
        return cb
    p.when_idle().addCallback(run_again)
    reactor.callWhenRunning(rem_call, p, 'test', True)
    reactor.callWhenRunning(rem_call, p, 'test2', False)
    reactor.callWhenRunning(rem_call, p, 'test_exc', False)
    reactor.callWhenRunning(rem_call, p, 'test_exc2', False)
    reactor.callLater(10, reactor.listenTCP, 54123, server.Site(TestHandler(), timeout=60), interface='localhost')
    reactor.run()

