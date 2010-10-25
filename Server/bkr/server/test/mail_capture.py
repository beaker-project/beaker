# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
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
A fake SMTP server which runs in its own thread. Use this in tests to capture 
e-mails sent by Beaker and assert their contents.

See bkr.server.test.selenium.test_systems for an example of how to use this.
"""

import threading
import smtpd
import asyncore
import logging

log = logging.getLogger(__name__)

class MailCaptureThread(threading.Thread):

    def __init__(self, **kwargs):
        # XXX smtpd.SMTPServer uses asyncore, which keeps a global map 
        # of open connections -- that is really bad! This thread should have its
        # own map, otherwise it will interfere with any other threads using asyncore.
        # Sadly smtpd.SMTPServer does not give us any nice way to do that :-(
        # For now this works because we don't have any other threads using asyncore
        # in our tests.
        assert not asyncore.socket_map
        super(MailCaptureThread, self).__init__(**kwargs)
        self.daemon = True
        self._running = True
        self.captured_mails = []

    def stop(self):
        self._running = False
        self.join()

    def run(self):
        captured_mails = self.captured_mails
        class CapturingSMTPServer(smtpd.SMTPServer):
            def process_message(self, peer, mailfrom, rcpttos, data):
                log.debug('%r: Captured mail from peer %r: %r', self, peer,
                        (mailfrom, rcpttos, data))
                captured_mails.append((mailfrom, rcpttos, data))
        server = CapturingSMTPServer(('127.0.0.1', 19999), None)
        log.debug('Spawning %r', server)
        try:
            while self._running:
                asyncore.loop(timeout=1, count=1)
        finally:
            server.close()
