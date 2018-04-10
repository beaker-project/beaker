
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import email
from turbogears.database import session
from selenium.common.exceptions import NoSuchElementException
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import get_server_base, login, logout
from bkr.inttest import data_setup, mail_capture_thread

class SystemAction(WebDriverTestCase):

    @classmethod
    def setUpClass(cls):
        with session.begin():
            cls.owner_email_address = data_setup.unique_name(u'picard%s@starfleet.gov')
            cls.system_owner = data_setup.create_user(
                email_address=cls.owner_email_address)
            cls.system_fqdn = data_setup.unique_name('ncc1701d%s')
            cls.system = data_setup.create_system(fqdn=cls.system_fqdn,
                owner=cls.system_owner)
            lc = data_setup.create_labcontroller()
            cls.system.lab_controller = lc
            lender = u'amd'
            location = u'bne'
            vendor = u'intel'
            cls.system.lender = lender
            cls.system.location = location
            cls.system.vendor = vendor
            cls.reporter_email_address = data_setup.unique_name(u'crusher%s@starfleet.gov')
            cls.problem_reporter = data_setup.create_user(password=u'password',
                display_name=data_setup.unique_name('Crusher Lady%s'),
                email_address=cls.reporter_email_address)
            cls.problem_reporter.use_old_job_page = True

    def setUp(self):
        b = self.browser = self.get_browser()
        try:
            login(b, user=self.problem_reporter.user_name, password='password')
        except NoSuchElementException:
            pass #Already logged in

    def _std_check_mail(self, sender, rcpts, raw_msg, notification, payload, subject,
        system=None, reporter=None):
        if not system:
            system = self.system
        if not reporter:
            reporter = self.problem_reporter
        self.assertEqual(rcpts, [system.owner.email_address,
                reporter.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['From'],
                r'"%s \(via Beaker\)" <%s>' % (reporter.display_name, reporter.email_address ))
        self.assertEqual(msg['To'], '%s' % system.owner.email_address)
        self.assertEqual(msg['Subject'], '%s' % subject)
        self.assertEqual(msg['Cc'], reporter.email_address)
        self.assertEqual(msg['X-Beaker-Notification'], notification)
        self.assertEqual(msg['X-Lender'], system.lender)
        self.assertEqual(msg['X-Owner'], system.owner.user_name)
        self.assertEqual(msg['X-Location'], system.location)
        self.assertEqual(msg['X-Lab-Controller'], system.lab_controller.fqdn)
        self.assertEqual(msg['X-Vendor'], system.vendor)
        self.assertEqual(msg['X-Type'], system.type.value)
        # This will break with multiple arched system...
        self.assertEqual(msg['X-Arch'], system.arch[0].arch)
        self.assertEqual(msg.get_payload(decode=True),payload)

    def test_anonymous_cant_contact_owner(self):
        b = self.browser
        logout(b)
        # Test can't access when not logged in
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('Loan').click()
        b.find_element_by_xpath('//div[@id="loan" and not(.//button[text()="Request Loan"])]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=652334
    def test_system_activity_entry_is_correctly_truncated(self):
        with session.begin():
            system = data_setup.create_system()
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_xpath('//button[text()="Report problem"]').click()
        b.find_element_by_name('message').send_keys(u'a' + u'\u044f' * 100)
        b.find_element_by_xpath('//button[text()="Report"]').click()
        # Wait for our success box
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Report sent"]')

    def test_reporter_and_system_cc_list_are_cced(self):
        with session.begin():
            interested_party_email = data_setup.unique_name(u'%sinterestedparty1@example.invalid')
            system = data_setup.create_system()
            system.cc = [interested_party_email]
        mail_capture_thread.start_capturing()
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_xpath('//button[text()="Report problem"]').click()
        b.find_element_by_name('message').send_keys('I broke it')
        b.find_element_by_xpath('//button[text()="Report"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Report sent"]')
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        self.assertEqual(rcpts, [system.owner.email_address,
                self.problem_reporter.email_address, interested_party_email])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['Cc'], '%s, %s' % (self.problem_reporter.email_address,
                interested_party_email))

    def test_report_problem_via_recipe(self):
        with session.begin():
            owner = data_setup.create_user()
            job = data_setup.create_completed_job(owner=owner)
        mail_capture_thread.start_capturing()
        b = self.browser
        b.get(get_server_base() + 'recipes/%s' % job.recipesets[0].recipes[0].id)
        b.find_element_by_link_text('Report Problem with System').click()
        b.find_element_by_id('problem_description').send_keys('I broke it')
        b.find_element_by_xpath('//input[@value=\'Report\']').click()
        b.find_element_by_xpath('//div/span[text()=\'Success\']')
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)

    def test_report_problem(self):
        mail_capture_thread.start_capturing()
        b = self.browser

        # Test can send problem report succesfully
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath('//button[text()="Report problem"]').click()
        b.find_element_by_name('message').send_keys('testing problem')
        b.find_element_by_xpath('//button[text()="Report"]').click()
        # Wait for our success box
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Report sent"]')
        # Check the email was sent
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEquals(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        payload = 'A Beaker user has reported a problem with system \n' \
            '%s <%sview/%s>.\n\n' \
            'Reported by: %s\n\n' \
            'Problem description:\n' \
            'testing problem' \
            % (self.system_fqdn, get_server_base(), self.system_fqdn,
                self.problem_reporter.display_name)
        self._std_check_mail(sender, rcpts, raw_msg, 'system-problem',
            payload, 'Problem reported for %s' % self.system.fqdn)

    def test_loan_request(self):
        mail_capture_thread.start_capturing()
        b = self.browser

        # Test can send loan request succesfully
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('Loan').click()
        b.find_element_by_xpath('//button[text()="Request Loan"]').click()
        b.find_element_by_name('message').send_keys('request loan')
        b.find_element_by_xpath('//button[text()="Request"]').click()
        # Wait for our success box
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Request sent"]')
        # Check the email was sent
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEquals(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        payload = 'A Beaker user has requested you loan them the system\n' \
            '%s <%sview/%s>.\n' \
            'Here is a copy of their request:\n' \
            'request loan\n Requested by: %s' \
            % (self.system_fqdn, get_server_base(), self.system_fqdn,
                self.problem_reporter.display_name)
        self._std_check_mail(sender, rcpts, raw_msg, 'loan-request',
            payload, 'Loan request for %s' % self.system.fqdn)
