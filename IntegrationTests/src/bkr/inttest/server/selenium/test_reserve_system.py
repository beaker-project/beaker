#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, is_text_present, \
        search_for_system
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import Arch, ExcludeOSMajor, SystemType, LabControllerDistroTree
from selenium.webdriver.support.ui import Select
import unittest, time, re, os
from turbogears.database import session

class ReserveWorkflow(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.system = data_setup.create_system(arch=u'i386')
        self.system2 = data_setup.create_system(arch=u'x86_64')
        self.unique_distro_name = data_setup.unique_name('distro%s')
        self.distro = data_setup.create_distro(name=self.unique_distro_name)
        self.distro_tree_i386 = data_setup.create_distro_tree(
                variant=u'Server', arch=u'i386', distro=self.distro)
        self.distro_tree_x86_64= data_setup.create_distro_tree(
                variant=u'Server', arch=u'x86_64', distro=self.distro)

        self.system.lab_controller = self.lc
        self.system.shared = True
        self.system2.lab_controller = self.lc
        self.system2.shared = True

        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_reserve_multiple_arch_got_distro(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('tag')).select_by_visible_text('None selected')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        s = Select(b.find_element_by_name('distro_tree_id'))
        s.select_by_visible_text('%s Server i386' % self.distro.name)
        s.select_by_visible_text('%s Server x86_64' % self.distro.name)
        b.find_element_by_xpath('//button[@class="auto_pick"]').click()
        self.assertEquals(b.find_element_by_id('form_distro').text,
                '%s Server i386, %s Server x86_64'
                % (self.distro.name, self.distro.name))
        self.assertEquals(b.title, 'Reserve System Any System')

    def test_no_lab_controller_distro(self):
        """ Test distros that have no lab controller are not shown"""
        with session.begin():
            self.distro_tree_i386.lab_controller_assocs[:] = []
        login(self.browser)
        #Selecting multiple arch
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('tag')).select_by_visible_text('None selected')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        options = b.find_elements_by_xpath('//select[@name="distro_tree_id"]/option')
        self.assert_(not any('i386' in option.text for option in options), options)

    # https://bugzilla.redhat.com/show_bug.cgi?id=630902
    def test_filtering_by_lab_controller(self):
        with session.begin():
            self.distro_tree_x86_64.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=self.lc, url=u'http://whatever')]
            other_lc = data_setup.create_labcontroller()
            self.distro_tree_i386.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=other_lc, url=u'http://whatever')]
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('tag')).select_by_visible_text('None selected')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('lab_controller_id'))\
            .select_by_visible_text(self.lc.fqdn)
        b.find_element_by_xpath('//select[@name="distro_tree_id" '
                'and ./option and not(./option[text()="i386"])]')

    def test_reserve_multiple_arch_tag_got_distro(self):
        with session.begin():
            self.distro.tags.append(u'FOO')
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('tag')).select_by_visible_text('FOO')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)

    def test_reserve_single_arch(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('tag')).select_by_visible_text('None selected')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_xpath('//button[@class="auto_pick"]').click()
        self.assertEquals(b.find_element_by_id('form_distro').text,
                '%s Server i386' % self.distro.name)
        self.assertEquals(b.title, 'Reserve System Any System')

def go_to_reserve_systems(browser, distro_tree):
    browser.get(get_server_base() + 'reserve_system?distro_tree_id=%s' % distro_tree.id)

def is_results_table_empty(browser):
    rows = browser.find_elements_by_xpath('//table[@class="list"]//td')
    return len(rows) == 0

class ReserveSystem(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.system = data_setup.create_system(arch=u'i386')
            self.distro_tree = data_setup.create_distro_tree(arch=u'i386')
            self.system.lab_controller = self.lc
            self.system.shared = True
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_show_all_columns_work(self):
        pass_ ='password'
        with session.begin():
            user = data_setup.create_user(password=pass_)
        b = self.browser
        login(b, user=user.user_name, password=pass_)

        go_to_reserve_systems(b, self.distro_tree)
        b.find_element_by_link_text('Toggle Search').click()
        b.find_element_by_xpath("//select[@id='systemsearch_0_table']"
            + "/option[@value='System/Name']").click()
        b.find_element_by_xpath("//select[@id='systemsearch_0_operation']"
            + "/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='systemsearch_0_value']") \
            .send_keys(self.system.fqdn)
        b.find_element_by_link_text('Toggle Result Columns').click()
        b.find_element_by_link_text('Select All').click()
        b.find_element_by_xpath("//form[@id='searchform']").submit()
        columns = b.find_elements_by_xpath("//table[@id='widget']//th")
        self.assertEquals(len(columns), 31)

    def test_exluded_distro_system_not_there(self):
        with session.begin():
            self.system.excluded_osmajor.append(ExcludeOSMajor(
                    osmajor=self.distro_tree.distro.osversion.osmajor,
                    arch=self.distro_tree.arch))
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro_tree)
        search_for_system(b, self.system)
        b.implicitly_wait(0)
        self.assert_(is_results_table_empty(b))
        b.implicitly_wait(10)

        with session.begin():
            self.system.arch.append(Arch.by_name(u'x86_64')) # Make sure it still works with two archs
        go_to_reserve_systems(b, self.distro_tree)
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
        go_to_reserve_systems(b, self.distro_tree)
        search_for_system(b, self.system)
        self.assert_(is_text_present(b, 'Reserve Now'))

        logout(b)
        login(b, user=user_2.user_name, password=pass_)
        go_to_reserve_systems(b, self.distro_tree)
        search_for_system(b, self.system)
        self.assert_(is_text_present(b, 'Queue Reservation'))

    def test_by_distro(self):
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro_tree)
        search_for_system(b, self.system)
        self.failUnless(is_text_present(b, self.system.fqdn))
        b.find_element_by_link_text('Reserve Now').click()
        b.find_element_by_name('whiteboard').send_keys(unicode(self.distro_tree))
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
        go_to_reserve_systems(b, self.distro_tree)
        search_for_system(b, group_system)
        b.implicitly_wait(0)
        self.assert_(is_results_table_empty(b))

if __name__ == "__main__":
    unittest.main()
