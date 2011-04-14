#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class SystemHasUserCanLoan(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.user = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.user)
        self.system.user = self.user 
        session.flush()

    def tearDown(self):
        self.selenium.stop()

    def test_can_loan(self):
        self.login()
        sel = self.selenium
        sel.open('view/%s' % self.system.fqdn)
        
        sel.wait_for_page_to_load("30000")
        # This is the (Loan) link...
        sel.click("//div[@id='fedora-content']/div[1]/form/div/table/tbody/tr[9]/td[2]/a/span") 
        sel.wait_for_page_to_load("30000")
        sel.type("Loan_user", "%s" % self.user.user_name)
        sel.click("//input[@value='Change']")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("%s Loaned to %s" % (self.system.fqdn,self.user.user_name)))

