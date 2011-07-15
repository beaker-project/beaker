
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
