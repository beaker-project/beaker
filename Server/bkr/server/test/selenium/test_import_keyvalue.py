#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class ImportKeyValue(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.csv_file_name = 'utf8.csv'
        self.project_path = os.getcwd() 
        self.package_path = 'bkr/server/test/selenium'
        self.csv_file = os.path.join(self.project_path,self.package_path,self.csv_file_name)
    
    def test_keyvalue(self):
        sel = self.selenium
        sel.open("/")
        try:
            self.logout()
        except: pass
        self.login() 
        sel.click("link=Import")
        sel.wait_for_page_to_load("3000")
        sel.type("import_csv_file", "%s" % self.csv_file)
        sel.click("//input[@value='Import CSV']")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("No Errors"))
 
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
