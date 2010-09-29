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

import unittest
import logging
import email
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test.mail_capture import MailCaptureThread
from bkr.server.test import data_setup

class TestSystemView(SeleniumTestCase):

    slow = True

    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.mail_capture = MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.selenium.stop()
        self.mail_capture.stop()

    def go_to_system_view(self):
        sel = self.selenium
        sel.open('')
        sel.type('simplesearch', self.system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('3000')
        sel.click('link=%s' % self.system.fqdn)
        sel.wait_for_page_to_load('3000')

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.assertEquals(self.selenium.get_title(), self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=623603
    # see also TestRecipeView.test_can_report_problem
    def test_can_report_problem(self):
        sel = self.selenium
        self.go_to_system_view()
        sel.click('link=(Report problem)')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(self.selenium.get_title(),
                'Report a problem with %s' % self.system.fqdn)
        self.assertEqual(
                # value of cell beside "Problematic system" cell
                sel.get_text('//form[@name="report_problem"]//table//td'
                    '[preceding-sibling::th[1]/text() = "Problematic system"]'),
                self.system.fqdn)
        sel.type('report_problem_problem_description', 'b0rk b0rk b0rk')
        sel.submit('report_problem')
        sel.wait_for_page_to_load('20000')
        self.assertEqual(sel.get_text('css=div.flash'),
                'Your problem report has been forwarded to the system owner')
        # assert the problem report e-mail
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        self.assertEqual(rcpts, [self.system_owner.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['to'], self.system_owner.email_address)
        self.assertEqual(msg['subject'], 'Problem reported for %s' % self.system.fqdn)
        self.assertEqual(msg.get_payload(),
                'A Beaker user has reported a problem with system %s.\n\n\n'
                'Problem description:\nb0rk b0rk b0rk' % self.system.fqdn)
