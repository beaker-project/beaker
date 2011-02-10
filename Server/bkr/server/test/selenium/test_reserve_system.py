#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

def click_reserve_now(sel, system):
    """
    On the /reserve_system page, click the Reserve Now link corresponding 
    to the given system.
    """
    sel.click('//table[@id="widget"]//td[a/text()="Reserve Now" '
            'and preceding-sibling::td[7]/a/text() = "%s"]/a'
            % system.fqdn)

class ReserveSystem(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.lc = data_setup.create_labcontroller()
        self.system = data_setup.create_system(arch=u'i386')
        self.distro = data_setup.create_distro(arch=u'i386')
        data_setup.create_task(name=u'/distribution/install')
        data_setup.create_task(name=u'/distribution/reservesys')
        self.system.lab_controller = self.lc
        self.system.shared = True
        session.flush()
    
    def test_by_distro(self):
        self.login()
        sel = self.selenium
        sel.open("distros/")
        sel.type("simplesearch", "%s" % self.distro.name)
        sel.click("search")
        sel.wait_for_page_to_load("3000")
        sel.click("link=Pick System")
        sel.wait_for_page_to_load("3000")
        self.failUnless(sel.is_text_present("%s" % self.system.fqdn))
        click_reserve_now(sel, self.system)
        sel.wait_for_page_to_load("30000")
        sel.type("form_whiteboard", self.distro.name)
        sel.click("//input[@value='Queue Job']")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Success"))
        except AssertionError, e: self.verificationErrors.append(str(e))

    # https://bugzilla.redhat.com/show_bug.cgi?id=672134
    def test_admin_can_reserve_any_system(self):
        group_system = data_setup.create_system(shared=True)
        group_system.lab_controller = self.lc
        group_system.groups.append(data_setup.create_group())
        session.flush()
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        sel.open('distros/')
        sel.type('simplesearch', self.distro.name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=Pick System')
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present(group_system.fqdn))
        click_reserve_now(sel, group_system)
        sel.wait_for_page_to_load('30000')
        sel.click('//input[@value="Queue Job"]')
        sel.wait_for_page_to_load('30000')
        self.failUnless(sel.is_text_present('Success'))
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
