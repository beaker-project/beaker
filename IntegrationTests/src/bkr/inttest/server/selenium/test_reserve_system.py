
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import lxml.etree
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, \
        search_for_system, check_system_search_results
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import Arch, ExcludeOSMajor, SystemType, \
        LabControllerDistroTree, SystemPermission, TaskBase, SystemStatus
from selenium.webdriver.support.ui import Select
import unittest, time, re, os
from turbogears.database import session

WORKFLOW_DESCR = "Reserve Workflow provision of distro %s on %s for %s seconds"

class ReserveWorkflow(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.system = data_setup.create_system(arch=u'i386', shared=True,
                                               lab_controller=self.lc)
        self.system2 = data_setup.create_system(arch=u'x86_64', shared=True,
                                                lab_controller=self.lc)
        self.unique_distro_name = data_setup.unique_name('distro%s')
        self.distro = data_setup.create_distro(name=self.unique_distro_name)
        self.distro_tree_i386 = data_setup.create_distro_tree(
                variant=u'Server', arch=u'i386', distro=self.distro)
        self.distro_tree_x86_64= data_setup.create_distro_tree(
                variant=u'Server', arch=u'x86_64', distro=self.distro)

        self.browser = self.get_browser()

    def test_default_tag_is_none_selected(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'reserveworkflow/')
        selected_options = Select(b.find_element_by_name('tag')). \
            all_selected_options
        # There should only be one selected option
        self.assertTrue(len(selected_options), 1)
        self.assertEquals(selected_options[0].text, 'None selected')

    def test_reserve_multiple_arch_got_distro(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        s = Select(b.find_element_by_name('distro_tree_id'))
        s.select_by_visible_text('%s Server i386' % self.distro.name)
        s.select_by_visible_text('%s Server x86_64' % self.distro.name)
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        b.find_element_by_xpath('//h1[contains(string(.), "J:")]')
        # two recipe sets, one for each distro tree
        self.assertEquals(len(b.find_elements_by_class_name('recipeset')), 2)
        b.find_element_by_xpath('//td[normalize-space(string(.))="%s Server i386"]'
                % self.distro.name)
        b.find_element_by_xpath('//td[normalize-space(string(.))="%s Server x86_64"]'
                % self.distro.name)

    def test_no_lab_controller_distro(self):
        """ Test distros that have no lab controller are not shown"""
        with session.begin():
            self.distro_tree_i386.lab_controller_assocs[:] = []
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        # wait for the distro_tree_id select to be populated
        b.find_element_by_xpath('//select[@name="distro_tree_id"]'
                '/option[normalize-space(.)="%s Server x86_64"]' % self.distro.name)
        options = b.find_elements_by_xpath('//select[@name="distro_tree_id"]/option')
        self.assert_(not any('i386' in option.text for option in options), options)

    # https://bugzilla.redhat.com/show_bug.cgi?id=630902
    # Previously "lab" was a filter for distro trees, now it is a filter for 
    # systems. Picking an incompatible distro tree and lab filter should show 
    # an error when trying to submit the job, which is what we test for now.
    def test_filtering_by_lab_controller(self):
        with session.begin():
            self.distro_tree_x86_64.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=self.lc, url=u'http://whatever')]
            other_lc = data_setup.create_labcontroller()
            self.distro_tree_i386.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=other_lc, url=u'http://whatever')]
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id')).select_by_visible_text(
                '%s Server i386' % self.distro.name)
        b.find_element_by_xpath(
                '//label[contains(string(.), "Any system from lab:")]'
                '/input[@type="radio"]').click()
        Select(b.find_element_by_name('lab')).select_by_visible_text(self.lc.fqdn)
        b.find_element_by_xpath('//button[text()="Submit job"]').click()
        self.assertIn('%s Server i386 is not available on %s'
                    % (self.distro.name, self.lc.fqdn),
                b.find_element_by_class_name('alert-error').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1062086
    def test_no_matching_systems(self):
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'Fedora21',
                    distro_name=u'Fedora-21', variant=u'Server',
                    arch=u'aarch64', lab_controllers=[self.lc])
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor')).select_by_visible_text('Fedora21')
        Select(b.find_element_by_name('distro')).select_by_visible_text('Fedora-21')
        Select(b.find_element_by_name('distro_tree_id')).select_by_visible_text(
                'Fedora-21 Server aarch64')
        b.find_element_by_xpath(
                '//label[contains(string(.), "Any system from lab:")]'
                '/input[@type="radio"]').click()
        Select(b.find_element_by_name('lab')).select_by_visible_text(self.lc.fqdn)
        b.find_element_by_xpath('//button[text()="Submit job"]').click()
        self.assertIn('No available systems',
                b.find_element_by_class_name('alert-error').text)
        b.find_element_by_xpath(
                '//label[normalize-space(string(.))="Any system"]'
                '/input[@type="radio"]').click()
        b.find_element_by_xpath('//button[text()="Submit job"]').click()
        self.assertIn('No available systems',
                b.find_element_by_class_name('alert-error').text)

    def test_reserve_multiple_arch_tag_got_distro(self):
        with session.begin():
            self.distro.tags.append(u'FOO')
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('tag')).select_by_visible_text('FOO')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)

    def test_reserve_single_arch(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        b.find_element_by_xpath('//h1[contains(string(.), "J:")]')
        wb_descr = (WORKFLOW_DESCR %
                    (self.distro.name, "any system", "86400"))
        wboard = b.find_element_by_class_name('job-whiteboard')
        self.assertIn(wb_descr, wboard.text, msg="Fail to match default whiteboard")
        # one recipe set for the chosen distro tree
        self.assertEquals(len(b.find_elements_by_class_name('recipeset')), 1)
        b.find_element_by_xpath('//td[normalize-space(string(.))="%s Server i386"]'
                % self.distro.name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1188539
    def test_uses_new_check_install_task(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        jid = b.find_element_by_xpath('//h1//span[@class="job-id"]').text
        with session.begin():
            job = TaskBase.get_by_t_id(jid)
            # first task in the recipe should be our new check-install task
            first_task = job.recipesets[0].recipes[0].tasks[0]
            self.assertEquals(first_task.task.name, '/distribution/check-install')

    def test_reserve_time(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_name('reserve_duration').clear()
        b.find_element_by_name('reserve_duration').send_keys('96')
        b.find_element_by_xpath('.//button[text()="Hours"]').click()
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        jid = b.find_element_by_xpath('//h1//span[@class="job-id"]').text
        with session.begin():
            job = TaskBase.get_by_t_id(jid)
            reserve_task = job.recipesets[0].recipes[0].tasks[1]
            self.assertEquals(reserve_task.task.name, '/distribution/reservesys')
            self.assertEquals(reserve_task.params[0].name, 'RESERVETIME')
            self.assertEquals(reserve_task.params[0].value, '345600') # 4 days in seconds

    # https://bugzilla.redhat.com/show_bug.cgi?id=1284368
    def test_html5_invalid_if_reserve_time_exceeds_maximum(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_name('reserve_duration').clear()
        b.find_element_by_name('reserve_duration').send_keys('604800')
        self.assertEqual(
            'reserve_duration',
            b.find_element_by_css_selector('input:invalid').get_attribute('name'))

    def test_reserve_time_defaults_to_day_in_seconds(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow/')
        self.assertEqual(
            u'86400',
            b.find_element_by_name('reserve_duration').get_attribute('value'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1122659
    def test_only_reserves_machines(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('tag')).select_by_visible_text('None selected')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        job_id = b.find_element_by_xpath('//h1//span[@class="job-id"]').text
        with session.begin():
            job = TaskBase.get_by_t_id(job_id)
            recipe = job.recipesets[0].recipes[0]
            self.assertEquals(recipe.host_requires,
                    u'<hostRequires><system_type value="Machine"/></hostRequires>')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1144205
    def test_preserves_lab_requirement(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'reserveworkflow')
        Select(b.find_element_by_name('osmajor'))\
            .select_by_visible_text(self.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(self.distro.name)
        Select(b.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text('%s Server i386' % self.distro.name)
        b.find_element_by_xpath(
                '//label[contains(string(.), "Any system from lab:")]'
                '/input[@type="radio"]').click()
        Select(b.find_element_by_name('lab')).select_by_visible_text(self.lc.fqdn)
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        job_id = b.find_element_by_xpath('//h1//span[@class="job-id"]').text
        wb_descr = (WORKFLOW_DESCR %
                    (self.distro.name, "any lab system", "86400"))
        wboard = b.find_element_by_class_name('job-whiteboard')
        self.assertIn(wb_descr, wboard.text, msg="Fail to match default whiteboard")
        with session.begin():
            job = TaskBase.get_by_t_id(job_id)
            cloned_job_xml = lxml.etree.tostring(job.to_xml(clone=True), encoding=unicode)  # cloning re-parses hostRequires
            self.assertIn(
                    u'<hostRequires><labcontroller op="=" value="%s"/>'
                    u'<system_type op="=" value="Machine"/></hostRequires>'
                    % self.lc.fqdn,
                    cloned_job_xml)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1093226
    def test_can_reserve_manual_system(self):
        with session.begin():
            broken_system = data_setup.create_system(arch=u'i386', shared=True,
                                                     status=SystemStatus.broken,
                                                     lab_controller=self.lc)
            manual_system = data_setup.create_system(arch=u'i386', shared=True,
                                                     status=SystemStatus.manual,
                                                     lab_controller=self.lc)
        b = self.browser
        login(b)
        # broken system should not be present
        go_to_reserve_systems(b, distro_tree=self.distro_tree_i386)
        search_for_system(b, broken_system)
        check_system_search_results(b, absent=[broken_system])
        # provision manual system
        go_to_reserve_systems(b, distro_tree=self.distro_tree_i386)
        search_for_system(b, manual_system)
        row = b.find_element_by_xpath('//tr[normalize-space(string(td))="%s"]' % manual_system.fqdn)
        row.find_element_by_link_text('Reserve Now').click()
        b.find_element_by_xpath('//button[normalize-space(text())="Submit job"]').click()
        # should end up on the job page
        job_id = b.find_element_by_xpath('//h1//span[@class="job-id"]').text
        wb_descr = (WORKFLOW_DESCR %
                    ("None", "a specific system", "86400"))
        wboard = b.find_element_by_class_name('job-whiteboard')
        self.assertIn(wb_descr, wboard.text, msg="Fail to match default whiteboard")
        with session.begin():
            job = TaskBase.get_by_t_id(job_id)
            cloned_job_xml = lxml.etree.tostring(job.to_xml(clone=True), encoding=unicode)  # cloning re-parses hostRequires
            self.assertIn(
                u'<hostRequires force="%s"/>' % manual_system.fqdn,
                cloned_job_xml)

def go_to_reserve_systems(browser, distro_tree=None):
    b = browser
    b.get(get_server_base() + 'reserveworkflow/')
    if distro_tree:
        Select(b.find_element_by_name('osmajor')).select_by_visible_text(
                distro_tree.distro.osversion.osmajor.osmajor)
        Select(b.find_element_by_name('distro')).select_by_visible_text(
                distro_tree.distro.name)
        Select(b.find_element_by_name('distro_tree_id')).select_by_visible_text(
                unicode(distro_tree))
    browser.find_element_by_xpath(
            '//div[contains(string(.//label), "Specific system:")]'
            '//a[text()="Select"]').click()
    browser.find_element_by_xpath('//h1[text()="Reserve Systems"]')

class ReserveSystem(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.system = data_setup.create_system(arch=u'i386', shared=True)
            # The distro tree is only on this lab controller, so when we are 
            # picking systems we won't be shown any others left in the db.
            self.distro_tree = data_setup.create_distro_tree(arch=u'i386',
                    lab_controllers=[self.lc])
            self.system.lab_controller = self.lc
        self.browser = self.get_browser()

    def test_show_all_columns_work(self):
        pass_ ='password'
        with session.begin():
            user = data_setup.create_user(password=pass_)
        b = self.browser
        login(b, user=user.user_name, password=pass_)

        go_to_reserve_systems(b, self.distro_tree)
        b.find_element_by_link_text('Show Search Options').click()
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
        self.assertEquals(len(columns), 34)

    def test_all_systems_included_when_no_distro_tree_selected(self):
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, distro_tree=None)
        search_for_system(b, self.system)
        check_system_search_results(b, present=[self.system])

    def test_exluded_distro_system_not_there(self):
        with session.begin():
            self.system.excluded_osmajor.append(ExcludeOSMajor(
                    osmajor=self.distro_tree.distro.osversion.osmajor,
                    arch=self.distro_tree.arch))
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro_tree)
        check_system_search_results(b, absent=[self.system])

        with session.begin():
            self.system.arch.append(Arch.by_name(u'x86_64')) # Make sure it still works with two archs
        go_to_reserve_systems(b, self.distro_tree)
        check_system_search_results(b, absent=[self.system])

    def test_loaned_not_used_system_not_shown(self):
        with session.begin():
            pass_ ='password'
            user_1 = data_setup.create_user(password=pass_)
            user_2 = data_setup.create_user(password=pass_)
            self.system.loaned = user_1
        b = self.browser
        login(b, user=user_1.user_name, password=pass_)
        go_to_reserve_systems(b, self.distro_tree)
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '/td/a[text()="Reserve Now"]' % self.system.fqdn)

        logout(b)
        login(b, user=user_2.user_name, password=pass_)
        go_to_reserve_systems(b, self.distro_tree)
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '/td/a[text()="Queue Reservation"]' % self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1099142
    def test_prototype_systems_are_shown(self):
        # The scheduler will *not* pick a Prototype normally, but Reserve 
        # Workflow will show you them if you have access, and then 
        # <hostRequires force=""/> will let you use it even if the scheduler 
        # would have skipped it otherwise.
        with session.begin():
            self.system.type = SystemType.prototype
        b = self.browser
        login(b)
        go_to_reserve_systems(b, self.distro_tree)
        check_system_search_results(b, present=[self.system])

    def test_by_distro(self):
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro_tree)
        #https://bugzilla.redhat.com/show_bug.cgi?id=1154887
        search_for_system(b, self.system)
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '/td/a[text()="Reserve Now"]' % self.system.fqdn).click()
        b.find_element_by_name('whiteboard').send_keys(unicode(self.distro_tree))
        b.find_element_by_xpath('//button[text()="Submit job"]').click()
        # we should end up on the job page
        b.find_element_by_xpath('//h1[contains(string(.), "J:")]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=722321
    def test_admin_cannot_reserve_any_system(self):
        with session.begin():
            group_system = data_setup.create_system(shared=False)
            group_system.lab_controller = self.lc
            group_system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve,
                    group=data_setup.create_group())
        login(self.browser)
        b = self.browser
        go_to_reserve_systems(b, self.distro_tree)
        check_system_search_results(b, absent=[group_system])
