
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import datetime
import requests
import email
from selenium.webdriver.support.ui import WebDriverWait
from bkr.server.model import SystemActivity, System, SystemPermission
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.requests_utils import login as requests_login, post_json, patch_json
from bkr.inttest.server.webdriver_utils import login, logout
from bkr.inttest import data_setup, with_transaction, get_server_base, DatabaseTestCase, \
        mail_capture_thread
from turbogears.database import session

class SystemLoanTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.browser = self.get_browser()
        self.owner = data_setup.create_user(password=u'password')
        self.system = data_setup.create_system(owner=self.owner, shared=False)

    def go_to_loan_page(self):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath('//ul[contains(@class, "system-nav")]'
                '//a[text()="Loan"]').click()

    def change_loan(self, loanee, comment=None, expect_success=True):
        b = self.browser
        tab = b.find_element_by_id('loan')
        tab.find_element_by_xpath('.//button[text()="Lend"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('recipient').send_keys(loanee)
        if comment:
            modal.find_element_by_name('comment').send_keys(comment)
        modal.find_element_by_tag_name('form').submit()
        if expect_success:
            # Wait for modal to close itself
            b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')

    def borrow(self):
        b = self.browser
        tab = b.find_element_by_id('loan')
        tab.find_element_by_xpath('.//button[text()="Borrow"]').click()

    def return_loan(self):
        b = self.browser
        tab = b.find_element_by_id('loan')
        tab.find_element_by_xpath('.//button[text()="Return Loan"]').click()

    def verify_loan_update(self, user):
        b = self.browser
        tab = b.find_element_by_id('loan')
        if user:
            tab.find_element_by_xpath('.//p[contains(text(), '
                    '"The system is currently loaned to")]')
            tab.find_element_by_xpath('.//a[text()="%s"]' % user)
        else:
            tab.find_element_by_xpath('.//p[text()="The system is not currently loaned."]')

    def verify_loan_error(self, error):
        b = self.browser
        modal = b.find_element_by_class_name('modal')
        self.assertIn(error, 
                modal.find_element_by_class_name('alert-error').text)
        # https://bugzilla.redhat.com/show_bug.cgi?id=1144203
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[text()="Save changes"]')

    def test_return_loan(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        # Login as admin, loan to average Joe,
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        logout(b)

        # Login as average Joe, and click 'Return Loan'
        login(b, user.user_name, 'password')
        self.go_to_loan_page()
        self.return_loan()
        self.verify_loan_update('')
        logout(b)

        # Login as admin, loan to self and add comment
        login(b)
        comment = u'As I pee, sir, I see Pisa!'
        self.go_to_loan_page()
        self.change_loan(u'admin', comment)
        self.verify_loan_update(u'admin')
        sys = self.system
        # Test going from '' -> comment in SystemActivity
        sys_activity_comment = sys.dyn_activity.filter(SystemActivity.field_name == \
            u'Loan Comment').first()
        self.assertEqual(sys_activity_comment.old_value, u'')
        self.assertEqual(sys_activity_comment.new_value, comment)
        # Let's return the loan
        self.return_loan()
        self.verify_loan_update('')
        # Test going from 'admin' -> '' in SystemActivity
        sys = System.by_fqdn(self.system.fqdn, user)
        sys_activity_name = sys.dyn_activity.filter(SystemActivity.field_name == \
            u'Loaned To').first()
        self.assertEqual(sys_activity_name.old_value, u'admin')
        self.assertEqual(sys_activity_name.new_value, u'')
        # Test going from comment -> '' in SystemActivity
        sys_activity_comment2 = sys.dyn_activity.filter(SystemActivity.field_name == \
            u'Loan Comment').first()
        self.assertEqual(sys_activity_comment2.old_value, comment)
        self.assertEqual(sys_activity_comment2.new_value, u'')

    def test_ajax_loan_change_is_persisted(self):
        with session.begin():
            user = data_setup.create_user()
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        self.verify_loan_update(user.user_name)
        # Reload page
        self.go_to_loan_page()
        self.verify_loan_update(user.user_name)
        # Test going from '' -> user in SystemActivity
        sys = self.system
        sys_activity = sys.dyn_activity.filter(SystemActivity.field_name ==
            u'Loaned To').first()
        self.assertEqual(sys_activity.old_value, u'')
        self.assertEqual(sys_activity.new_value, user.user_name)

    def test_can_add_comments_with_loanee(self):
        with session.begin():
            user = data_setup.create_user()
        b = self.browser
        login(b)
        self.go_to_loan_page()
        comment = 'Murder for a jar of red rum'
        self.change_loan(user.user_name, comment)
        self.verify_loan_update(user.user_name)
        # Reload page
        self.go_to_loan_page()
        tab = b.find_element_by_id('loan')
        loan_comment = tab.find_element_by_class_name('system-loan-comment').text
        self.assertEqual(comment, loan_comment)


    def test_can_lend_when_system_has_user(self):
        with session.begin():
            user = data_setup.create_user()
            self.system.user = user
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        self.verify_loan_update(user.user_name)

    def test_owner_can_borrow(self):
        p_word='password'
        with session.begin():
            user = data_setup.create_user(password=p_word)
            self.system.owner = user
        b = self.browser
        login(b, user=user.user_name, password=p_word)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        self.verify_loan_update(user.user_name)

    def test_can_not_change_loan_when_system_has_loanee_and_not_admin(self):
        p_word = 'password'
        with session.begin():
            user = data_setup.create_user(password=p_word)
            self.system.user = user
            self.system.loaned = user
        b = self.browser
        login(b, user=user.user_name, password=p_word)
        self.go_to_loan_page()
        tab = b.find_element_by_id('loan')
        tab.find_element_by_xpath('.//button[text()="Return Loan"]')
        self.assertNotIn('Borrow', tab.text)
        self.assertNotIn('Lend', tab.text)

    def test_can_change_loan_when_system_has_loanee(self):
        with session.begin():
            user = data_setup.create_user()
            user2 = data_setup.create_user()
            self.system.user = user
            self.system.loaned = user
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user2.user_name)
        self.verify_loan_update(user2.user_name)

        with session.begin():
            session.refresh(self.system)
            reserved_activity = self.system.activity[-1]
            self.assertEqual(reserved_activity.action, 'Changed')
            self.assertEqual(reserved_activity.field_name, 'Loaned To')
            self.assertEqual(reserved_activity.old_value, user.user_name)
            self.assertEqual(reserved_activity.new_value, user2.user_name)
            self.assertEqual(reserved_activity.service, 'HTTP')

    def test_user_with_perms_can_borrow(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.loan_self, user=user)
        b = self.browser
        login(b, user=user.user_name, password='password')
        self.go_to_loan_page()
        self.borrow()
        self.verify_loan_update(user.user_name)

    def test_user_with_borrow_perms_cannot_lend(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.loan_self, user=user)
            loanee_name = data_setup.create_user().user_name
        b = self.browser
        login(b, user=user.user_name, password='password')
        self.go_to_loan_page()
        tab = b.find_element_by_id('loan')
        tab.find_element_by_xpath('.//button[text()="Borrow"]')
        self.assertNotIn('Lend', tab.text)

    def test_cannot_lend_to_invalid_user(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.loan_any, user=user)
        b = self.browser
        login(b, user=user.user_name, password='password')
        self.go_to_loan_page()
        loanee_name = "this_is_not_a_valid_user_name_for_any_test"
        self.change_loan(loanee_name, expect_success=False)
        error = "user name %s is invalid" % loanee_name
        self.verify_loan_error(error)
        # check errors don't stack up
        # https://bugzilla.redhat.com/show_bug.cgi?id=1161373
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_tag_name('form').submit()
        modal.find_element_by_xpath('.//button[text()="Save changes"]')
        errors = modal.find_elements_by_class_name('alert-error')
        self.assertEquals(len(errors), 1, 'Multiple errors: %r' % errors)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1121748
    def test_cannot_lend_to_ldap_user_with_extra_whitespace(self):
        b = self.browser
        login(b, user=self.owner.user_name, password='password')
        self.go_to_loan_page()
        # jgillard is defined in ldap-data.ldif
        self.change_loan(u' jgillard', expect_success=False)
        error = 'user name jgillard is invalid'
        self.verify_loan_error(error)

class SystemLoanHTTPTest(DatabaseTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_lend_to_deleted_user(self):
        with session.begin():
            system = data_setup.create_system()
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'systems/%s/loans/' % system.fqdn,
                session=s, data={'recipient': {'user_name': deleted_user.user_name}})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text,
                'Cannot lend to deleted user %s' % deleted_user.user_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=996165
    def test_sends_mail_notification_for_loan(self):
        with session.begin():
            owner = data_setup.create_user(user_name='mturnbull', email_address='mturnbull@gov.au')
            system = data_setup.create_system(fqdn='lya3.aemo.com.au', owner=owner)
            loanee = data_setup.create_user(user_name='bshorten')
        s = requests.Session()
        requests_login(s)
        mail_capture_thread.start_capturing()
        response = post_json(get_server_base() + 'systems/%s/loans/' % system.fqdn,
                session=s, data={'recipient': {'user_name': 'bshorten'}})
        self.assertEquals(response.status_code, 200)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEquals(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEquals(['mturnbull@gov.au'], rcpts)
        self.assertEquals('mturnbull@gov.au', msg['To'])
        self.assertEquals('System lya3.aemo.com.au loaned to bshorten', msg['Subject'])
        self.assertEquals(
                'Beaker system lya3.aemo.com.au <%sview/lya3.aemo.com.au>\n'
                'has been loaned to bshorten by admin.'
                % get_server_base(),
                msg.get_payload(decode=True))

    # https://bugzilla.redhat.com/show_bug.cgi?id=996165
    def test_sends_mail_notification_for_loan_return(self):
        with session.begin():
            owner = data_setup.create_user(user_name='mturnbull', email_address='mturnbull@gov.au')
            system = data_setup.create_system(fqdn='lya4.aemo.com.au', owner=owner)
            loanee = data_setup.create_user(user_name='bshorten')
            system.loaned = loanee
        s = requests.Session()
        requests_login(s)
        mail_capture_thread.start_capturing()
        response = patch_json(get_server_base() + 'systems/%s/loans/+current' % system.fqdn,
                session=s, data={'finish': 'now'})
        self.assertEquals(response.status_code, 200)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEquals(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEquals(['mturnbull@gov.au'], rcpts)
        self.assertEquals('mturnbull@gov.au', msg['To'])
        self.assertEquals('System lya4.aemo.com.au loan returned', msg['Subject'])
        self.assertEquals(
                'Beaker system lya4.aemo.com.au <%sview/lya4.aemo.com.au>\n'
                'loan has been returned by admin.'
                % get_server_base(),
                msg.get_payload(decode=True))
