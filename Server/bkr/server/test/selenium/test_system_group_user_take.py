#!/usr/bin/python
import bkr.server.test.selenium
from turbogears.database import session
from bkr.server.test import data_setup
import unittest, time, os

class SystemGroupUserTake(bkr.server.test.selenium.SeleniumTestCase):

    """
    Tests the following scenarios for take in both Automated and Manual machines:
    * System with no groups
    * System has group, user not in group
    * System has group, user in group

    """
    
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()

        self.automated_system = data_setup.create_system()
        self.automated_system.shared = True
        self.manual_system = data_setup.create_system(status=u'Manual')
        self.manual_system.shared = True
        self.group = data_setup.create_group()
        self.user = data_setup.create_user(password='password') 
        lc = data_setup.create_labcontroller(u'test-lc')
        data_setup.add_system_lab_controller(self.automated_system,lc)
        data_setup.add_system_lab_controller(self.manual_system,lc)
        session.flush()
        self.login(user=self.user.user_name,password='password')
        #TODO need to login
        

    def test_system_no_group(self):
        #Auto Machine
        session.flush()
        sel = self.selenium
        sel.open("/")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("(Take)")) #Automated should not have Take for this user
        except AssertionError, e: self.verificationErrors.append('Take is present on automated machine with no groups')

        #Manual machine 
        #import pdb;pdb.set_trace()
        sel.open("/")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("(Take)")) #Should have Take for this machine
        except AssertionError, e: self.verificationErrors.append('Take is not present on manual machine with no groups')

    def test_system_has_group(self):
        #Automated machine
        data_setup.add_group_to_system(self.automated_system,self.group) # Add systemgroup
        session.flush()
        sel = self.selenium
        sel.open("/")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("(Take)")) #Should not be here
        except AssertionError, e: self.verificationErrors.append('Take is present on automated machine with group')

        #Manual machine
        data_setup.add_group_to_system(self.manual_system, self.group) # Add systemgroup
        session.flush()
        sel = self.selenium
        sel.open("/")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("(Take)")) #Should not be here
        except AssertionError, e: self.verificationErrors.append('Take is present on manual machine with group')

    def test_system_group_user_group(self):
        #Automated machine
        #import pdb;pdb.set_trace()
        data_setup.add_group_to_system(self.automated_system,self.group) # Add systemgroup
        data_setup.add_user_to_group(self.user,self.group) # Add user to group 
        session.flush()
        sel = self.selenium
        sel.open("/")
        sel.type("simplesearch", "%s" % self.automated_system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.automated_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("(Take)")) #Should be here
        except AssertionError, e: self.verificationErrors.append('Take is not available to automated machine with system group pirvs' )

        #Manual machine
        data_setup.add_group_to_system(self.manual_system, self.group) # Add systemgroup
        session.flush()
        sel = self.selenium
        sel.open("/")
        sel.type("simplesearch", "%s" % self.manual_system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.manual_system.fqdn)
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("(Take)")) #Should be here
        except AssertionError, e: self.verificationErrors.append('Take is not here for manual machine with system group privs')

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
