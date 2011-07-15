#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session

class ItemCount(SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        data_setup.create_device(device_class="IDE") #needed for device page
        data_setup.create_distro() # needed for distro page
        data_setup.create_job() # needed for job page
        data_setup.create_task() #create task
        system = data_setup.create_system()
        system.shared = True
        system.activity.append(data_setup.create_system_activity())
        session.flush()
    
    def test_itemcount(self):
        sel = self.selenium
        sel.open("")
        self.login()
        sel.click("link=All")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
        sel.click("link=Available")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
        sel.click("link=Free")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
        sel.click("//ul[@id='devices']/li[1]/a")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
        sel.click("//ul[@id='distros']/li[1]/a")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
        sel.click("link=Jobs")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
        sel.click("link=Task Library")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("Items found:"))
 
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
