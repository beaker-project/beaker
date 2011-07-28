#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
from bkr.server.model import Arch, ExcludeOSMajor
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

class ReserveSystem(SeleniumTestCase):
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
        self.login()

    def test_exluded_distro_system_not_there(self):
        sel = self.selenium
        self.system.excluded_osmajor.append(ExcludeOSMajor(osmajor=self.distro.osversion.osmajor, arch=self.system.arch[0]))
        session.flush()
        sel.open("reserve_system?arch=%s&distro_family=%s&tag=&distro=%s&search=Show+Systems" % (self.distro.arch, self.distro.osversion.osmajor, self.distro.install_name ))
        sel.wait_for_page_to_load(3000)
        self.assert_(self.system.fqdn not in sel.get_body_text())

        self.system.arch.append(Arch.by_name(u'x86_64')) # Make sure it still works with two archs
        session.flush()
        sel.open("reserve_system?arch=%s&distro_family=%s&tag=&distro=%s&search=Show+Systems" % (self.distro.arch, self.distro.osversion.osmajor, self.distro.install_name ))
        sel.wait_for_page_to_load(3000)
        self.assert_(self.system.fqdn not in sel.get_body_text())


    def test_loaned_not_used_system_not_shown(self):

        def _get_reserve_val():
            sel.open("reserve_system?distro=%s&simplesearch=%s&search=Search" % (self.distro.install_name, self.system.fqdn))
            sel.wait_for_page_to_load('30000')
            return sel.get_table("//table[@id='widget'].0.7")


        pass_ ='password'
        user_1 = data_setup.create_user(password=pass_)
        user_2 = data_setup.create_user(password=pass_)
        self.system.loaned = user_1
        session.flush()
        sel = self.selenium
        self.logout()
        self.login(user=user_1.user_name, password=pass_)
        can_reserve_now = _get_reserve_val()
        self.assert_(can_reserve_now == 'Reserve Now')

        self.logout()
        self.login(user=user_2.user_name, password=pass_)
        queue_reservation = _get_reserve_val()
        self.assert_(queue_reservation == 'Queue Reservation')
        
    
    def test_by_distro(self):
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=722321
    def test_admin_cannot_reserve_any_system(self):
        group_system = data_setup.create_system(shared=True)
        group_system.lab_controller = self.lc
        group_system.groups.append(data_setup.create_group())
        session.flush()
        sel = self.selenium
        sel.open('distros/')
        sel.type('simplesearch', self.distro.name)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=Pick System')
        sel.wait_for_page_to_load('30000')
        self.failUnless(not sel.is_text_present(group_system.fqdn))
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
