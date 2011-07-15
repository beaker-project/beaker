from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session

class SystemAvailable(SeleniumTestCase):
 
    def setUp(self):
        self.selenium = self.get_selenium()
        self.password = 'password'
        self.user_1 = data_setup.create_user(password=self.password)
        self.user_2 = data_setup.create_user(password=self.password)
        self.system = data_setup.create_system(shared=True)
        lc = data_setup.create_labcontroller()
        self.system.lab_controller = lc
        session.flush()
        self.selenium.start()
        try:
            self.login(user=self.user_1,password=self.password)
        except Exception:
            pass

    def test_avilable_with_no_loan(self):
        sel = self.selenium
        sel.open('available')
        sel.wait_for_page_to_load('3000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system.fqdn)
        sel.click("Search")
        sel.wait_for_page_to_load('3000')
        self.failUnless(sel.is_text_present("%s" % self.system.fqdn))
        sel.open("view/%s" % self.system.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))

    def test_avilable_with_loan(self):
        sel = self.selenium
        self.system.loaned=self.user_2
        session.flush()
        sel.open('available')
        sel.wait_for_page_to_load('3000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system.fqdn)
        sel.click("Search")
        sel.wait_for_page_to_load('3000')
        self.failUnless(sel.is_text_present("%s" % self.system.fqdn))
        sel.open("view/%s" % self.system.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))

    def tearDown(self):
        self.selenium.stop()

