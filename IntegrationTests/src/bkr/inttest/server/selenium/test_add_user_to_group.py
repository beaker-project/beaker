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
        with session.begin():
            self.BEAKER_TEST_USER_1 = data_setup.create_user(password='password')
            self.BEAKER_TEST_USER_2 = data_setup.create_user(password='password')
            self.GROUP = data_setup.create_group()

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
        sel.type("GroupUser_user_text", "%s" % self.BEAKER_TEST_USER_1.user_name)
        sel.click("//input[@value='Add']")
        sel.wait_for_page_to_load("30000")
        #Test user 1 is in group admin
        self.failUnless(sel.is_text_present("%s" % self.BEAKER_TEST_USER_1.user_name))
        #Test that user 2 is NOT in admin group
        self.failUnless(not sel.is_text_present("%s" % self.BEAKER_TEST_USER_2.user_name))

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
        sel.click("link=%s" % self.GROUP.group_name)
        sel.wait_for_page_to_load("30000")
        sel.type("GroupUser_user_text", "%s" % self.BEAKER_TEST_USER_2.user_name)
        sel.click("//input[@value='Add']")
        sel.wait_for_page_to_load("30000")
        #Test user 2 is in group
        self.failUnless(sel.is_text_present("%s" % self.BEAKER_TEST_USER_2.user_name))
        #Test that user 1 is NOT in group
        self.failUnless(not sel.is_text_present("%s" % self.BEAKER_TEST_USER_1.user_name))

    def test_user_group_is_updated(self):
        with session.begin():
            group = data_setup.create_group()
        sel = self.selenium
        self.login()
        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % group.group_name)
        sel.wait_for_page_to_load("30000")
        sel.type("GroupUser_user_text", "%s" % self.BEAKER_TEST_USER_2.user_name)
        sel.click("//input[@value='Add']")
        sel.wait_for_page_to_load("30000")
        sel.open('users/edit?id=%d' % self.BEAKER_TEST_USER_2.user_id)
        sel.wait_for_page_to_load("30000")
        self.assert_(group.display_name in sel.get_text('//table[@id="groups_grid"]'))

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
