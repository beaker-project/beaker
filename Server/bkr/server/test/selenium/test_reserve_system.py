#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class ReserveSystem(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.lc = data_setup.create_labcontroller()
        self.system = data_setup.create_system(fqdn=u'test_reserve_system',arch=u'i386')
        self.distro = data_setup.create_distro(name=u'test_reserve_system_distro')
        data_setup.create_task(task_name=u'/distribution/install')
        data_setup.append_distro_to_lc(self.distro,self.lc)
        self.system.lab_controller = self.lc
        self.system.shared = True
        session.flush()
    
    def test_by_distro(self):
        try:
            self.logout() 
        except: pass
        self.login()
        sel = self.selenium
        sel.open("/distros/")
        sel.type("simplesearch", "%s" % self.distro.name)
        sel.click("search")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Pick System")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("%s" % self.system.fqdn))
        sel.click("link=Reserve Now")
        sel.wait_for_page_to_load("30000")
        sel.type("form_whiteboard", "testing")
        sel.type("form_whiteboard", "test_reserve_system_distro")
        sel.click("//input[@value='Queue Job']")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Success"))
        except AssertionError, e: self.verificationErrors.append(str(e))

    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
