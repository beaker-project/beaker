#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class Menu(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        try:
            self.logout() 
        except:pass
        self.login()
    
    def test_my_menu(self):
        sel = self.selenium
        try:
            sel.open("/")
            sel.click("link=My Jobs")
            sel.wait_for_page_to_load("3000")
            sel.click("link=My Recipes")
            sel.wait_for_page_to_load("3000")
            sel.click("link=My Systems")
            sel.wait_for_page_to_load("3000")
        except Exception, e: 
            self.verificationErrors.append(str(e))
         
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
