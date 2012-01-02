#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, is_text_present
from bkr.inttest import data_setup, get_server_base
from bkr.server.model import Arch, ExcludeOSMajor
from selenium.webdriver.support.ui import Select
import unittest, time, re, os
from turbogears.database import session

def go_to_reserve_systems(browser, distro):
    browser.get(get_server_base() + 'distros/')
    browser.find_element_by_name('simplesearch').send_keys(distro.name)
    browser.find_element_by_name('distrosearch_simple').submit()
    browser.find_element_by_link_text('Pick System').click()

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

def search_for_system(browser, system):
    browser.find_element_by_link_text('Toggle Search').click()
    Select(browser.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Name')
    Select(browser.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
    browser.find_element_by_name('systemsearch-0.value').send_keys(system.fqdn)
    browser.find_element_by_name('systemsearch').submit()

def is_results_table_empty(browser):
    rows = browser.find_elements_by_xpath('//table[@class="list"]//td')
    return len(rows) == 0

class ReserveSystem(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.system = data_setup.create_system(arch=u'i386')
            self.distro = data_setup.create_distro(arch=u'i386')
            data_setup.create_task(name=u'/distribution/install')
            data_setup.create_task(name=u'/distribution/reservesys')
            self.system.lab_controller = self.lc
            self.system.shared = True
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_exluded_distro_system_not_there(self):
        with session.begin():
            self.system.excluded_osmajor.append(ExcludeOSMajor(
                    osmajor=self.distro.osversion.osmajor,
                    arch=self.distro.arch))
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, self.system)
        b.implicitly_wait(0)
        self.assert_(is_results_table_empty(b))
        b.implicitly_wait(10)

        with session.begin():
            self.system.arch.append(Arch.by_name(u'x86_64')) # Make sure it still works with two archs
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, self.system)
        b.implicitly_wait(0)
        self.assert_(is_results_table_empty(b))

    def test_loaned_not_used_system_not_shown(self):
        with session.begin():
            pass_ ='password'
            user_1 = data_setup.create_user(password=pass_)
            user_2 = data_setup.create_user(password=pass_)
            self.system.loaned = user_1
        b = self.browser
        login(b, user=user_1.user_name, password=pass_)
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, self.system)
        self.assert_(is_text_present(b, 'Reserve Now'))

        logout(b)
        login(b, user=user_2.user_name, password=pass_)
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, self.system)
        self.assert_(is_text_present(b, 'Queue Reservation'))

    def test_by_distro(self):
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, self.system)
        self.failUnless(is_text_present(b, self.system.fqdn))
        b.find_element_by_link_text('Reserve Now').click()
        b.find_element_by_name('whiteboard').send_keys(self.distro.name)
        b.find_element_by_id('form').submit()
        self.assert_('Success' in b.find_element_by_css_selector('.flash').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=722321
    def test_admin_cannot_reserve_any_system(self):
        with session.begin():
            group_system = data_setup.create_system(shared=True)
            group_system.lab_controller = self.lc
            group_system.groups.append(data_setup.create_group())
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, group_system)
        b.implicitly_wait(0)
        self.assert_(is_results_table_empty(b))

    # https://bugzilla.redhat.com/show_bug.cgi?id=740957
    def test_reserve_workflow_does_not_list_virtual_systems(self):
        with session.begin():
            virtual_system = data_setup.create_system(shared=True,
                    lab_controller=self.lc, type=SystemType.virtual)
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro)
        search_for_system(b, virtual_system)
        b.implicitly_wait(0)
        self.assert_(is_results_table_empty(b))

if __name__ == "__main__":
    unittest.main()
