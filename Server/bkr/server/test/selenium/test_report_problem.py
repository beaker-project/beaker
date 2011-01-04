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
from bkr.server.test import data_setup, get_server_base

class TestReportProblem(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.mail_capture = MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.selenium.stop()
        self.mail_capture.stop()

    def test_can_report_problem(self):
        system_owner = data_setup.create_user(
                email_address=u'picard@starfleet.gov')
        system = data_setup.create_system(fqdn=u'ncc1701d',
                owner=system_owner)
        problem_reporter = data_setup.create_user(password=u'password',
                display_name=u'Beverley Crusher',
                email_address=u'crusher@starfleet.gov')
        session.flush()
        self.login(user=problem_reporter.user_name, password='password')
        sel = self.selenium
        sel.open('report_problem?system_id=%s' % system.id)
        self.assertEqual(sel.get_title(), 'Report a problem with ncc1701d')
        self.assertEqual(
                # value of cell beside "Problematic system" cell
                sel.get_text('//form[@name="report_problem"]//table//td'
                    '[preceding-sibling::th[1]/text() = "Problematic system"]'),
                system.fqdn)
        sel.type('report_problem_problem_description', 'Make it so!')
        sel.submit('report_problem')
        sel.wait_for_page_to_load('20000')
        self.assertEqual(sel.get_text('css=div.flash'),
                'Your problem report has been forwarded to the system owner')
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        self.assertEqual(rcpts, [system_owner.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['From'],
                r'"Beverley Crusher \(via Beaker\)" <crusher@starfleet.gov>')
        self.assertEqual(msg['To'], 'picard@starfleet.gov')
        self.assertEqual(msg['Subject'], 'Problem reported for ncc1701d')
        self.assertEqual(msg['X-Beaker-Notification'], 'system-problem')
        self.assertEqual(msg['X-Beaker-System'], 'ncc1701d')
        self.assertEqual(msg.get_payload(decode=True),
                'A Beaker user has reported a problem with system \n'
                'ncc1701d <%sview/ncc1701d>.\n\n'
                'Reported by: Beverley Crusher\n\n'
                'Problem description:\n'
                'Make it so!'
                % get_server_base())

    def test_reporting_problem_requires_login(self):
        problem_reporter = data_setup.create_user(password=u'password')
        system = data_setup.create_system(fqdn=u'ncc1701e')
        session.flush()
        sel = self.selenium
        try:
            sel.open('report_problem?system_id=%s' % system.id)
            sel.wait_for_page_to_load('3000')
            self.fail('Should raise 403')
        except Exception, e:
            self.assert_('Response_Code = 403' in e.args[0])
        sel.type('user_name', problem_reporter.user_name)
        sel.type('password', 'password')
        sel.click('login')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(sel.get_title(), 'Report a problem with ncc1701e')

    # https://bugzilla.redhat.com/show_bug.cgi?id=652334
    def test_system_activity_entry_is_correctly_truncated(self):
        system = data_setup.create_system()
        session.flush()
        self.login()
        sel = self.selenium
        sel.open('report_problem?system_id=%s' % system.id)
        sel.type('report_problem_problem_description', u'a' + u'\u044f' * 100)
        sel.submit('report_problem')
        sel.wait_for_page_to_load('20000')
        self.assertEqual(sel.get_text('css=div.flash'),
                'Your problem report has been forwarded to the system owner')
