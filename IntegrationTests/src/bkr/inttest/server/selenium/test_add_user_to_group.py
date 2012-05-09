#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session

class TestAddUserToGroup(SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.BEAKER_TEST_USER_1 = data_setup.create_user(password='password').user_name
        self.BEAKER_TEST_USER_2 = data_setup.create_user(password='password').user_name
        self.GROUP = data_setup.create_group().group_name
        session.flush()

    
    def test_add_user_to_admin_group(self):
        sel = self.selenium
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("30000")
        sel.type("user_name", self.BEAKER_LOGIN_USER)
        sel.type("password", self.BEAKER_LOGIN_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("30000")
        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load("30000")
        sel.click("link=admin")
        sel.wait_for_page_to_load("30000")
        sel.type("GroupUser_user_text", "%s" % self.BEAKER_TEST_USER_1)
        sel.click("//input[@value='Add']")
        sel.wait_for_page_to_load("30000")
        #Test user 1 is in group admin
        try: self.failUnless(sel.is_text_present("%s" % self.BEAKER_TEST_USER_1))
        except AssertionError, e: self.verificationErrors.append('Could  not find user %s in users in %s' % (self.BEAKER_TEST_USER_1, self.test_add_user_to_admin_group.__name__))
        #Test that user 2 is NOT in admin group
        try: self.failUnless(not sel.is_text_present("%s" % self.BEAKER_TEST_USER_2))
        except AssertionError, e: self.verificationErrors.append('User %s was found in group that they were not added to in %s' % (self.BEAKER_TEST_USER_2, self.test_add_user_to_admin_group.__name__))

    def test_add_user_to_nonadmin_group(self):
        sel = self.selenium
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("30000")
        sel.type("user_name", self.BEAKER_LOGIN_USER)
        sel.type("password", self.BEAKER_LOGIN_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("30000")
        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % self.GROUP)
        sel.wait_for_page_to_load("30000")
        sel.type("GroupUser_user_text", "%s" % self.BEAKER_TEST_USER_2)
        sel.click("//input[@value='Add']")
        sel.wait_for_page_to_load("30000")
        #Test user 2 is in group 
        try: self.failUnless(sel.is_text_present("%s" % self.BEAKER_TEST_USER_2))
        except AssertionError, e: self.verificationErrors.append('Could  not find user %s in users in %s' % (self.BEAKER_TEST_USER_2, self.test_add_user_to_nonadmin_group.__name__))
        #Test that user 1 is NOT in group
        try: self.failUnless(not sel.is_text_present("%s" % self.BEAKER_TEST_USER_1))
        except AssertionError, e: self.verificationErrors.append('User %s was found in group that they were not added to' % (self.BEAKER_TEST_USER_1, self.test_add_user_to_nonadmin_group.__name__))

    def tearDown(self):
	self.selenium.stop()
	self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()

