#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os

class AddUser(SeleniumTestCase):

    BEAKER_DISABLE_USER = os.environ.get('BEAKER_TEST_USER_2','disabled')
    BEAKER_DISABLE_EMAIL = os.environ.get('BEAKER_TEST_USER_2','disabled@my.com')
    BEAKER_DISABLE_PASSWORD = os.environ.get('BEAKER_TEST_PASSWORD_2','password')
    BEAKER_TEST_USER_2 = os.environ.get('BEAKER_TEST_USER_2','anonymous2')
    BEAKER_TEST_EMAIL_2 = os.environ.get('BEAKER_TEST_USER_2','anonymous2@my.com')
    BEAKER_TEST_PASSWORD_2 = os.environ.get('BEAKER_TEST_PASSWORD_2','password')
    BEAKER_TEST_USER_1 = os.environ.get('BEAKER_TEST_USER_1','anonymous')
    BEAKER_TEST_EMAIL_1 = os.environ.get('BEAKER_TEST_USER_1','anonymous@my.com')
    BEAKER_TEST_PASSWORD_1 = os.environ.get('BEAKER_TEST_PASSWORD_1','password')

    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
    
    def test_adduser(self):
        sel = self.selenium
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("3000")
        sel.type("user_name", data_setup.ADMIN_USER)
        sel.type("password", data_setup.ADMIN_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Accounts")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Add ( + )")
        sel.wait_for_page_to_load("3000")
        sel.type("User_user_name", "%s" % self.BEAKER_TEST_USER_1)
        sel.type("User_display_name", "%s" % self.BEAKER_TEST_USER_1)
        sel.type("User_email_address", "%s" % self.BEAKER_TEST_EMAIL_1)
        sel.type("User_password", "%s" % self.BEAKER_TEST_PASSWORD_1)
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("3000")
        #Test Saved message came up
        try: self.failUnless(sel.is_text_present("saved"))
        except AssertionError, e: self.verificationErrors.append(str(e))
   
        sel.open("users")
        #Test that user 1 is listed as part of users
        try: self.failUnless(sel.is_text_present("%s" % self.BEAKER_TEST_USER_1))
        except AssertionError, e: self.verificationErrors.append(str(e)) 
   
        #Add user 2
        sel.click("link=Add ( + )")
        sel.wait_for_page_to_load("3000")
        sel.type("User_user_name", "%s" % self.BEAKER_TEST_USER_2)
        sel.type("User_display_name", "%s" % self.BEAKER_TEST_USER_2)
        sel.type("User_email_address", "%s" % self.BEAKER_TEST_EMAIL_2)
        sel.type("User_password", "%s" % self.BEAKER_TEST_PASSWORD_2)
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("3000")
        #Test Saved message came up
        try: self.failUnless(sel.is_text_present("%s saved" % self.BEAKER_TEST_USER_2))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.open("users")
        #Test that user 2 is listed as part of users
        try: self.failUnless(sel.is_text_present("%s" % self.BEAKER_TEST_USER_2))
        except AssertionError, e: self.verificationErrors.append(str(e)) 


    def test_disable(self):
        sel = self.selenium
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("3000")
        sel.type("user_name", data_setup.ADMIN_USER)
        sel.type("password", data_setup.ADMIN_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Accounts")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Add ( + )")
        sel.wait_for_page_to_load("3000")
        sel.type("User_user_name", "%s" % self.BEAKER_DISABLE_USER)
        sel.type("User_display_name", "%s" % self.BEAKER_DISABLE_USER)
        sel.type("User_email_address", "%s" % self.BEAKER_DISABLE_EMAIL)
        sel.type("User_password", "%s" % self.BEAKER_DISABLE_PASSWORD)
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("3000")
        #Test Saved message came up
        self.failUnless(sel.is_text_present("saved"))
        self.logout()

        # First verify you can login as user.
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("3000")
        sel.type("user_name", self.BEAKER_DISABLE_USER)
        sel.type("password", self.BEAKER_DISABLE_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("%s" % self.BEAKER_DISABLE_USER))
        self.logout()

        # Login as admin and disable user TEST 1
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("3000")
        sel.type("user_name", data_setup.ADMIN_USER)
        sel.type("password", data_setup.ADMIN_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Accounts")
        sel.wait_for_page_to_load("3000")
        sel.click("link=%s" % self.BEAKER_DISABLE_USER)
        sel.wait_for_page_to_load("3000")
        sel.click("User_disabled")
        sel.click("//input[@value='Save']")
        sel.wait_for_page_to_load("3000")
        self.logout()

        # Try and login as TEST User
        sel.open("")
        sel.click("link=Login")
        sel.wait_for_page_to_load("3000")
        sel.type("user_name", self.BEAKER_DISABLE_USER)
        sel.type("password", self.BEAKER_DISABLE_PASSWORD)
        sel.click("login")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("The credentials you supplied were not correct or did not grant access to this resource" ))


    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
