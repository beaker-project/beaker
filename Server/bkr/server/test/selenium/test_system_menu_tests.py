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

        self.BEAKER_LOGIN_USER = data_setup.create_user(password='password').user_name
        self.BEAKER_LOGIN_PASSWORD = 'password'
        data_setup.create_device(device_class="IDE")
        session.flush()
        self.login()
       
    def test_menulist(self):
        sel = self.selenium
        sel.open("")
        sel.click("link=All")
        sel.wait_for_page_to_load("3000")
        sel.click("link=My Systems") 
        sel.wait_for_page_to_load("3000")
        sel.click("link=Available")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Free")
        sel.wait_for_page_to_load("3000")
        sel.click("link=All")
        sel.wait_for_page_to_load("30000")
        sel.click("link=IDE")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Family")
        sel.wait_for_page_to_load("3000")
        sel.click("link=New Job")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Watchdog")
        sel.wait_for_page_to_load("3000")
        sel.click("//ul[@id='Activity']/li[1]/a")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Systems")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Distros")
        sel.wait_for_page_to_load("3000")
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
