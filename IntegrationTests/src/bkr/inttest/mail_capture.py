
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
A fake SMTP server which runs in its own thread. Use this in tests to capture 
e-mails sent by Beaker and assert their contents.

See bkr.server.test.selenium.test_systems for an example of how to use this.
"""

import threading
import smtpd
import asyncore
import logging

log = logging.getLogger(__name__)

class CapturingSMTPServer(smtpd.SMTPServer):

    def __init__(self, localaddr, remoteaddr):
        # XXX smtpd.SMTPServer uses asyncore, which keeps a global map 
        # of open connections -- that is really bad! This thread should have its
        # own map, otherwise it will interfere with any other threads using asyncore.
        # Sadly smtpd.SMTPServer does not give us any nice way to do that :-(
        # For now this works because we don't have any other threads using asyncore
        # in our tests.
        assert not asyncore.socket_map, asyncore.socket_map
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        self._running = True
        # If the fake server is "running" but not "capturing" that means it
        # will just discard any received mails.
        self.capturing = False
        self.captured_mails = []
        # This event will be set on the first mail captured after start_capturing is called.
        self.has_captured = threading.Event()

    def process_message(self, peer, mailfrom, rcpttos, data):
        if self.capturing:
            log.debug('Captured mail from peer %r: %r', peer,
                    (mailfrom, rcpttos, data))
            self.captured_mails.append((mailfrom, rcpttos, data))
            self.has_captured.set()
        else:
            log.debug('Discarded mail for %r', rcpttos)

    def close(self):
        smtpd.SMTPServer.close(self)
        # also clean up any orphaned SMTP channels
        for dispatcher in asyncore.socket_map.values():
            if isinstance(dispatcher, smtpd.SMTPChannel) \
                    and dispatcher._SMTPChannel__server is self:
                log.debug('%r: Forcing close of orphaned channel %r',
                        self, dispatcher)
                dispatcher.close()

    def run(self):
        try:
            while self._running:
                asyncore.loop(timeout=1, count=1)
        finally:
            self.close()

    def stop(self):
        self._running = False

# Contrary to its name, this does not subclass Thread anymore, since we need to 
# be able to start it more than once in the same process. 
# bkr.inttest.setup_package() gets called by the main test suite but then again 
# by the beaker-server-redhat tests.
class MailCaptureThread(object):

    def start_capturing(self):
        if self.server.capturing:
            raise RuntimeError('%r is already capturing, missing a call to stop_capturing?')
        self.server.has_captured.clear()
        self.server.capturing = True

    def stop_capturing(self, wait=True):
        if wait:
            self.server.has_captured.wait(10)
            if not self.server.has_captured.is_set():
                raise RuntimeError('No mails captured')
        self.server.capturing = False
        captured_mails = list(self.server.captured_mails)
        self.server.captured_mails[:] = []
        return captured_mails

    def clear(self):
        self.server.capturing = False
        self.server.captured_mails[:] = []

    def stop(self):
        self.server.stop()
        self._thread.join()

    def start(self):
        self.server = CapturingSMTPServer(('127.0.0.1', 19999), None)
        log.debug('Spawning %r', self.server)
        self._thread = threading.Thread(target=self.server.run, name='MailCaptureThread-%s' % id(self))
        self._thread.daemon = True
        self._thread.start()
