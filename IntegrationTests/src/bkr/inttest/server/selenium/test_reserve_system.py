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


class ReserveWorkflow(SeleniumTestCase):
    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.system = data_setup.create_system(arch=u'i386')
        self.system2 = data_setup.create_system(arch=u'x86_64')
        self.unique_distro_name = data_setup.unique_name('distro%s')
        self.distro_i386 = data_setup.create_distro(arch=u'i386',name=self.unique_distro_name)
        self.distro_x86_64= data_setup.create_distro(arch=u'x86_64', name=self.unique_distro_name)
        self.distro_ia64 = data_setup.create_distro(arch=u'ia64')
        # Distro install_name is sans arch when displayed with multi arch options
        self.unique_distro_repr = re.sub(r'^(.+)\-(?:.+?)$',r'\1',self.distro_i386.install_name)

        data_setup.create_task(name=u'/distribution/install')
        data_setup.create_task(name=u'/distribution/reservesys')
        self.system.lab_controller = self.lc
        self.system.shared = True
        self.system2.lab_controller = self.lc
        self.system2.shared = True
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_reserve_multiple_arch_got_distro(self):
        self.login()
        #Selecting just arch
        sel = self.selenium
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.add_selection("reserveworkflow_form_arch", "label=x86_64")
        sel.select("reserveworkflow_form_tag", "label=None Selected")
        self.wait_for_condition(lambda: sel.is_text_present(self.unique_distro_repr))
        sel.select("reserveworkflow_form_distro", "label=%s" % self.unique_distro_repr)
        sel.click("reserveworkflow_form_auto_pick")
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_title(), 'Reserve System Any System')
        self.assert_(sel.is_text_present(self.distro_i386.install_name))
        self.assert_(sel.is_text_present(self.distro_x86_64.install_name))
      
        # Arch and family
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.add_selection("reserveworkflow_form_arch", "label=x86_64")
        sel.select("reserveworkflow_form_distro_family", "label=%s" % self.distro_i386.osversion.osmajor)
        sel.select("reserveworkflow_form_tag", "label=None Selected")
        self.wait_for_condition(lambda: sel.is_text_present(self.unique_distro_repr))
        sel.select("reserveworkflow_form_distro", "label=%s" % self.unique_distro_repr)
        sel.click("reserveworkflow_form_auto_pick")
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_title(), 'Reserve System Any System')
        self.assert_(sel.is_text_present(self.distro_i386.install_name))
        self.assert_(sel.is_text_present(self.distro_x86_64.install_name))

    def test_no_lab_controller_distro(self):
        """ Test distros that have no lab controller are not shown"""
        self.distro_i386.lab_controller_assocs[:] = []
        session.flush()
        self.login()
        #Selecting multiple arch
        sel = self.selenium
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.add_selection("reserveworkflow_form_arch", "label=x86_64")
        sel.select("reserveworkflow_form_tag", "label=None Selected")
        self.assertRaises(AssertionError,  self.wait_for_condition, lambda: sel.is_text_present(self.unique_distro_repr) == True, wait_time=5)
     
        # Single arch
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.select("reserveworkflow_form_tag", "label=None Selected")
        self.assertRaises(AssertionError,  self.wait_for_condition, lambda: sel.is_text_present(self.distro_i386.install_name) == True, wait_time=5)

    def test_reserve_multiple_arch_tag_got_distro(self):
        tag = data_setup.create_distro_tag(tag=u'FOO')
        self.distro_i386.tags.append(tag)
        self.distro_x86_64.tags.append(tag)
        session.flush()
        self.login()
        sel = self.selenium
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.add_selection("reserveworkflow_form_arch", "label=x86_64")
        sel.select("reserveworkflow_form_distro_family", "label=%s" % self.distro_i386.osversion.osmajor)
        sel.select("reserveworkflow_form_tag", "label=FOO")
        self.wait_for_condition(lambda: sel.is_text_present(self.unique_distro_repr))


    def test_reserve_single_arch(self):
        self.login()
        sel = self.selenium
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.select("reserveworkflow_form_distro_family", "label=%s" % self.distro_i386.osversion.osmajor)
        sel.select("reserveworkflow_form_tag", "label=None Selected")
        self.wait_for_condition(lambda: sel.is_text_present(self.distro_i386.install_name))
        sel.select("reserveworkflow_form_distro", "label=%s" % self.distro_i386.install_name)
        sel.click("reserveworkflow_form_auto_pick")
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_title(), 'Reserve System Any System')
        self.assert_(sel.is_text_present(self.distro_i386.install_name))

    def test_multiple_no_distro(self):
        self.login()
        sel = self.selenium
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.add_selection("reserveworkflow_form_arch", "label=ia64")
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        self.assertRaises(AssertionError,  self.wait_for_condition, lambda: sel.is_text_present(self.unique_distro_repr) == True, wait_time=5)

        tag = data_setup.create_distro_tag(u'BAR')
        self.distro_x86_64.tag = tag
        session.flush()
        sel = self.selenium
        sel.open("reserveworkflow")
        sel.wait_for_page_to_load('30000')
        sel.select("reserveworkflow_form_tag", "label=BAR")
        sel.add_selection("reserveworkflow_form_arch", "label=i386")
        sel.add_selection("reserveworkflow_form_arch", "label=x86_64")
        sel.select("reserveworkflow_form_distro_family", "label=%s" % self.distro_i386.osversion.osmajor)
        self.assertRaises(AssertionError,  self.wait_for_condition, lambda: sel.is_text_present(self.unique_distro_repr) == True, wait_time=5)


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
        sel.wait_for_page_to_load('30000')
        self.assert_(self.system.fqdn not in sel.get_body_text())

        self.system.arch.append(Arch.by_name(u'x86_64')) # Make sure it still works with two archs
        session.flush()
        sel.open("reserve_system?arch=%s&distro_family=%s&tag=&distro=%s&search=Show+Systems" % (self.distro.arch, self.distro.osversion.osmajor, self.distro.install_name ))
        sel.wait_for_page_to_load('30000')
        self.assert_(self.system.fqdn not in sel.get_body_text())


    def test_loaned_not_used_system_not_shown(self):

        def _get_reserve_val():
            sel.open("reserve_system?distro=%s&simplesearch=%s&search=Search" % (self.distro.install_name, self.system.fqdn))
            sel.wait_for_page_to_load('30000')
            return sel.get_text("//table[@id='widget']/tbody/tr[1]/td[8]")


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
        sel.wait_for_page_to_load('30000')
        sel.click("link=Pick System")
        sel.wait_for_page_to_load('30000')
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
