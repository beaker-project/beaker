
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session

class SystemLoanTest(SeleniumTestCase):
    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.system = data_setup.create_system()
        session.flush()

    def tearDown(self):
        self.selenium.stop()

    def go_to_loan_page(self):
        sel = self.selenium
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load("30000")
        sel.click('//table[@class="list"]//a[.//text()=" (Loan)"]')
        sel.wait_for_page_to_load("30000")

    def go_to_change_loan_page(self):
        sel = self.selenium
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load("30000")
        sel.click('//table[@class="list"]//a[.//text()=" (Change)"][preceding-sibling::a[text()=" (Return)"]]')
        sel.wait_for_page_to_load("30000")

    def test_can_loan_when_system_has_user(self):
        user = data_setup.create_user()
        self.system.user = user
        session.flush()
        self.login()
        self.go_to_loan_page()
        sel = self.selenium
        sel.type("Loan_user", user.user_name)
        sel.click("//input[@value='Change']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("%s Loaned to %s" %
                (self.system.fqdn, user.user_name)))

    def test_can_not_change_loan_when_system_has_loanee_and_not_admin(self):
        p_word = 'password'
        user = data_setup.create_user(password=p_word)
        self.system.user = user
        self.system.loaned = user
        session.flush()
        self.login(user=user.user_name, password=p_word)
        try:
            self.go_to_change_loan_page()
            self.fail("Should not get here")
        except Exception, e:
            if 'not found' not in str(e):
                raise

    def test_can_change_loan_when_system_has_loanee(self):
        user = data_setup.create_user()
        user2 = data_setup.create_user()
        self.system.user = user
        self.system.loaned = user
        session.flush()
        self.login()
        self.go_to_change_loan_page()
        sel = self.selenium
        sel.type("Loan_user", user2.user_name)
        sel.click("//input[@value='Change']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("%s Loaned to %s" %
                (self.system.fqdn, user2.user_name)))
        reserved_activity = self.system.activity[-1]
        self.assertEqual(reserved_activity.action, 'Changed')
        self.assertEqual(reserved_activity.field_name, 'Loaned To')
        self.assertEqual(reserved_activity.old_value, user.user_name)
        self.assertEqual(reserved_activity.new_value, user2.user_name)
        self.assertEqual(reserved_activity.service, 'WEBUI')

    def test_loan_username_autocomplete_works(self):
        user = data_setup.create_user(user_name=u'distinctiveusername')
        session.flush()
        self.login()
        self.go_to_loan_page()
        sel = self.selenium
        sel.focus('Loan_user')
        sel.type('Loan_user', '')
        sel.type_keys('Loan_user', 'distinc')
        self.wait_for_condition(lambda: sel.is_visible('autoCompleteResultsLoan_user'))
        self.assertEquals(sel.get_text('autoCompleteResultsLoan_user'),
                'distinctiveusername')
