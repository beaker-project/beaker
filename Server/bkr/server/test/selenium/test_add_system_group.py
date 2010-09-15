#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class AddSystemGroupTest(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        try:
            self.logout() 
        except: pass
        could_login = self.login()
        self.failUnless(could_login==True) 
        self.user_password = 'password' 
        self.user = data_setup.create_user(user_name=u'test_add_system_group',password=self.user_password)
        self.system = data_setup.create_system(fqdn=u'test1',owner=self.user)
        self.group = data_setup.create_group()
        data_setup.add_user_to_group(self.user,self.group)

                            
    def test_add_system_group(self):
        sel = self.selenium 
        sel.open("/view/%s" % self.system.fqdn)
        sel.click("//div[@id='fedora-content']/div[2]/ul/li[4]/a")
        sel.type("groups_group_text", "%s" % self.group.group_name)
        sel.click("//div[@id='fedora-content']/div[2]/div[4]/form/table/tbody/tr[2]/td[4]/a")
        sel.wait_for_page_to_load("30000")

        try:
            self.logout()
            self.login(self.user.user_name,self.user_password)
        except: raise
        sel.click("link=Available")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("%s" % self.system.fqdn))                                                                                                                    

def tearDown(self):
        self.selenium.stop()
                                                                                                                

if __name__ == "__main__":
    unittest.main()

