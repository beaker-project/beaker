
# vim: set fileencoding=utf-8:

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import datetime
import logging
from urlparse import urljoin
from urllib import urlencode, quote
import rdflib.graph
from turbogears.database import session

from bkr.inttest import data_setup, get_server_base, \
        assertions, with_transaction
from bkr.server.model import Arch, Key, Key_Value_String, Key_Value_Int, System, \
        Provision, ProvisionFamily, ProvisionFamilyUpdate, Hypervisor, \
        SystemStatus, LabInfo, ReleaseAction
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, check_system_search_results, \
        delete_and_confirm, logout, click_menu_item
from selenium.webdriver.support.ui import Select
from bkr.inttest.assertions import wait_for_condition

class SystemViewTestWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.system_owner = data_setup.create_user()
            self.unprivileged_user = data_setup.create_user(password=u'password')
            self.system = data_setup.create_system(lab_controller=self.lab_controller,
                    owner=self.system_owner, status=u'Automated', arch=u'i386')
            self.distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[self.lab_controller])
            self.system.provisions[self.distro_tree.arch] = Provision(
                    arch=self.distro_tree.arch, ks_meta=u'some_ks_meta_var=1',
                    kernel_options=u'some_kernel_option=1',
                    kernel_options_post=u'some_kernel_option=2')
            self.system.provisions[self.distro_tree.arch]\
                .provision_families[self.distro_tree.distro.osversion.osmajor] = \
                    ProvisionFamily(osmajor=self.distro_tree.distro.osversion.osmajor,
                        ks_meta=u'some_ks_meta_var=2', kernel_options=u'some_kernel_option=3',
                        kernel_options_post=u'some_kernel_option=4')
            self.system.provisions[self.distro_tree.arch]\
                .provision_families[self.distro_tree.distro.osversion.osmajor]\
                .provision_family_updates[self.distro_tree.distro.osversion] = \
                    ProvisionFamilyUpdate(osversion=self.distro_tree.distro.osversion,
                        ks_meta=u'some_ks_meta_var=3', kernel_options=u'some_kernel_option=5',
                        kernel_options_post=u'some_kernel_option=6')

        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=706150
    #https://bugzilla.redhat.com/show_bug.cgi?id=886875
    def test_kernel_install_options_propagated_view(self):

        with session.begin():
            self.system.provisions[self.distro_tree.arch] = \
                Provision(arch=self.distro_tree.arch,
                          ks_meta = u'key1=value1 key1=value2 key2=value key3',
                          kernel_options=u'key1=value1 key1=value2 key2=value key3',
                          kernel_options_post=u'key1=value1 key1=value2 key2=value key3')

        b = self.browser
        login(b)
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)

        # provision tab
        b.find_element_by_link_text('Provision').click()

        # select the distro
        Select(b.find_element_by_name('prov_install'))\
            .select_by_visible_text(unicode(self.distro_tree))

        # check the kernel install options field
        def provision_ks_meta_populated():
            if b.find_element_by_xpath("//input[@id='provision_ks_meta']")\
                    .get_attribute('value') == \
                    u'key1=value1 key1=value2 key2=value key3':
                return True



        # check the kernel install options field
        def provision_koptions_populated():
            if b.find_element_by_xpath("//input[@id='provision_koptions']")\
                    .get_attribute('value') == \
                    u'key1=value1 key1=value2 key2=value key3 noverifyssl':
                return True

        # check the kernel post install options field
        def provision_koptions_post_populated():
            if b.find_element_by_xpath("//input[@id='provision_koptions_post']")\
                    .get_attribute('value') == \
                    'key1=value1 key1=value2 key2=value key3':
                return True


        wait_for_condition(provision_ks_meta_populated)
        wait_for_condition(provision_koptions_populated)
        wait_for_condition(provision_koptions_post_populated)

    # https://bugzilla.redhat.com/show_bug.cgi?id=987313
    def test_labinfo_not_visible_for_new_systems(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath('//ul[@class="nav nav-tabs" and '
                'not(.//a/text()="Lab Info")]')

    def go_to_system_edit(self, system=None):
        if system is None:
            system = self.system
        b = self.browser
        self.go_to_system_view(system)
        b.find_element_by_link_text('Edit System').click()
        b.find_element_by_xpath('//h1[text()="%s"]' % system.fqdn)

    def go_to_system_view(self, system=None):
        if system is None:
            system = self.system
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_xpath('//title[normalize-space(text())="%s"]' % \
            system.fqdn)

    def assert_system_view_text(self, field, val):
        if field == 'fqdn':
            self.browser.find_element_by_xpath(
                    '//h1[normalize-space(text())="%s"]' % val)
        else:
            self.browser.find_element_by_xpath(
                    '//div[@class="controls" and preceding-sibling::label/@for="form_%s"]'
                    '/span[normalize-space(text())="%s"]'
                    % (field, val))

    def test_system_view_condition_report(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        self.assertFalse(b.find_element_by_id('condition_report_row').is_displayed())
        with session.begin():
            self.system.status = SystemStatus.broken
        self.go_to_system_view()
        self.assertTrue(b.find_element_by_id('condition_report_row').is_displayed())

    def test_current_job(self):
        b = self.browser
        login(b)
        with session.begin():
            job = data_setup.create_job(owner=self.system.owner,
                    distro_tree=self.distro_tree)
            data_setup.mark_job_running(job, system=self.system)
            job_id = job.id
        self.go_to_system_view()
        b.find_element_by_link_text('(Current Job)').click()
        b.find_element_by_xpath('//title[contains(text(), "J:%s")]' % job_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.browser.find_element_by_xpath('//title[text()="%s"]' % self.system.fqdn)

    def test_links_to_cc_change(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath( # link inside cell beside "Notify CC" cell
                '//div[normalize-space(label/text())="Notify CC"]'
                '//a[normalize-space(string(.))="Change"]').click()
        b.find_element_by_xpath('//title[text()="Notify CC list for %s"]'
                % self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=747086
    def test_update_system_no_lc(self):
        with session.begin():
            system = data_setup.create_system()
            system.labcontroller = None
        b = self.browser
        login(b)
        self.go_to_system_edit(system=system)
        new_fqdn = 'zx81.example.com'
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys(new_fqdn)
        b.find_element_by_link_text('Save Changes').click()
        self.assert_system_view_text('fqdn', new_fqdn)

    def test_update_system(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_edit()
        changes = {
            'fqdn': 'zx80.example.com',
            'vendor': 'Sinclair',
            'model': 'ZX80',
            'serial': '12345',
            'mac_address': 'aa:bb:cc:dd:ee:ff',
        }
        for k, v in changes.iteritems():
            b.find_element_by_name(k).clear()
            b.find_element_by_name(k).send_keys(v)
        b.find_element_by_link_text('Save Changes').click()
        for k, v in changes.iteritems():
            self.assert_system_view_text(k, v)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_status(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_edit()
        Select(b.find_element_by_name('status')).select_by_visible_text('Broken')
        b.find_element_by_link_text('Save Changes').click()
        self.assert_system_view_text('status', u'Broken')
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.status, SystemStatus.broken)
            self.assertEqual(len(self.system.status_durations), 2)
            self.assertEqual(self.system.status_durations[0].status,
                    SystemStatus.broken)
            assertions.assert_datetime_within(
                    self.system.status_durations[0].start_time,
                    tolerance=datetime.timedelta(seconds=60),
                    reference=datetime.datetime.utcnow())
            self.assert_(self.system.status_durations[0].finish_time is None)
            self.assert_(self.system.status_durations[1].finish_time is not None)
            assertions.assert_durations_not_overlapping(
                    self.system.status_durations)
            self.assert_(self.system.date_modified > orig_date_modified)

    # https://bugzilla.redhat.com/show_bug.cgi?id=746774
    def test_change_status_with_same_timestamps(self):
        # create two SystemStatusDuration rows with the same timestamp
        # (that is, within the same second)
        with session.begin():
            self.system.status = SystemStatus.removed
            session.flush()
            self.system.status = SystemStatus.automated
        b = self.browser
        login(b)
        self.go_to_system_edit()
        Select(b.find_element_by_name('status')).select_by_visible_text('Broken')
        b.find_element_by_link_text('Save Changes').click()
        b.find_element_by_xpath('//h1[text()="%s"]' % self.system.fqdn)
        self.assert_system_view_text('status', u'Broken')

    def test_strips_surrounding_whitespace_from_fqdn(self):
        b = self.browser
        login(b)
        self.go_to_system_edit()
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys('   lol   ')
        b.find_element_by_link_text('Save Changes').click()
        b.find_element_by_xpath('//h1[text()="lol"]')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.fqdn, u'lol')

    def test_rejects_malformed_fqdn(self):
        b = self.browser
        login(b)
        self.go_to_system_edit()
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys('lol...?')
        b.find_element_by_link_text('Save Changes').click()
        self.assertEquals(b.find_element_by_css_selector(
                '.control-group.error .help-inline').text,
                'The supplied value is not a valid hostname')

    def test_rejects_non_ascii_chars_in_fqdn(self):
        b = self.browser
        login(b)
        self.go_to_system_edit()
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys(u'lööööl')
        b.find_element_by_link_text('Save Changes').click()
        self.assertEquals(b.find_element_by_css_selector(
                '.control-group.error .help-inline').text,
                'The supplied value is not a valid hostname')

    # https://bugzilla.redhat.com/show_bug.cgi?id=683003
    def test_forces_fqdn_to_lowercase(self):
        b = self.browser
        login(b)
        self.go_to_system_edit()
        b.find_element_by_name('fqdn').clear()
        b.find_element_by_name('fqdn').send_keys('LooOOooL')
        b.find_element_by_link_text('Save Changes').click()
        b.find_element_by_xpath('//h1[text()="looooool"]')

    def test_add_arch(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Arch(s)"]').click()
        b.find_element_by_name('arch.text').send_keys('s390')
        b.find_element_by_name('arches').submit()
        b.find_element_by_xpath(
                '//div[@id="arches"]'
                '//td[normalize-space(text())="s390"]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    # https://bugzilla.redhat.com/show_bug.cgi?id=677951
    def test_add_nonexistent_arch(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Arch(s)"]').click()
        b.find_element_by_name('arch.text').send_keys('notexist')
        b.find_element_by_name('arches').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                u'No such arch notexist')

    def test_remove_arch(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Arch(s)"]').click()
        b.find_element_by_xpath(
                '//div[@id="arches"]'
                '//td[normalize-space(text())="i386"]')
        delete_and_confirm(b, '//tr[normalize-space(td[1]/text())="i386"]')
        self.assertEquals(b.find_element_by_class_name('flash').text, 'i386 Removed')
        b.find_element_by_xpath(
                '//div[@id="arches" and not(.//td[normalize-space(text())="i386"])]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_add_key_value(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Key/Values"]').click()
        b.find_element_by_name('key_name').send_keys('NR_DISKS')
        b.find_element_by_name('key_value').send_keys('100')
        b.find_element_by_name('keys').submit()
        b.find_element_by_xpath(
                '//td[normalize-space(preceding-sibling::td[1]/text())'
                '="NR_DISKS" and '
                'normalize-space(text())="100"]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_remove_key_value(self):
        with session.begin():
            self.system.key_values_int.append(
                    Key_Value_Int(Key.by_name(u'NR_DISKS'), 100))
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Key/Values"]').click()
        b.find_element_by_xpath(
                '//td[normalize-space(preceding-sibling::td[1]/text())'
                '="NR_DISKS" and '
                'normalize-space(text())="100"]')
        delete_and_confirm(b, '//tr[normalize-space(td[1]/text())="NR_DISKS" and '
                'normalize-space(td[2]/text())="100"]')
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'removed NR_DISKS/100')
        b.find_element_by_xpath('//div[@id="keys" and not(.//tr['
                'normalize-space(td[1]/text())="NR_DISKS" and '
                'normalize-space(td[2]/text())="100"])]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_add_group(self):
        with session.begin():
            group = data_setup.create_group()
            user_password = 'password'
            user = data_setup.create_user(password=user_password)
            data_setup.add_user_to_group(user, group)
            orig_date_modified = self.system.date_modified

        # as admin, assign the system to our test group
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Groups"]').click()
        b.find_element_by_name('group.text').send_keys(group.group_name)
        b.find_element_by_name('groups').submit()
        b.find_element_by_xpath(
                '//div[@id="groups"]'
                '//td[normalize-space(text())="%s"]' % group.group_name)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

        # as a user in the group, can we see it?
        logout(b)
        login(b, user.user_name, user_password)
        click_menu_item(b, 'Systems', 'Available')
        b.find_element_by_name('simplesearch').send_keys(self.system.fqdn)
        b.find_element_by_name('systemsearch_simple').submit()
        check_system_search_results(b, present=[self.system])

    def test_remove_group(self):
        with session.begin():
            group = data_setup.create_group()
            self.system.groups.append(group)
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Groups"]').click()
        b.find_element_by_xpath(
                '//td[normalize-space(text())="%s"]' % group.group_name)
        delete_and_confirm(b, '//tr[normalize-space(td[1]/text())="%s"]'
                % group.group_name)
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s Removed' % group.display_name)
        b.find_element_by_xpath(
                '//div[@id="groups" and not(.//td[normalize-space(text())="%s"])]'
                % group.group_name)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_power_quiescent_default_value(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc, with_power=False)
        b = self.browser
        login(b)
        self.go_to_system_view(system)
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Power Config"]').click()
        period = b.find_element_by_name('power_quiescent_period').get_attribute('value')
        self.assertEqual(period, str(5))

    def test_update_power_quiescent_validator(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Power Config"]').click()
        # Empty value
        b.find_element_by_name('power_quiescent_period').clear()
        b.find_element_by_xpath("//form[@id='power']").submit()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Power Config"]').click()
        error_text = b.find_element_by_xpath('//span[@class="help-block error"'
            ' and preceding-sibling::'
            'input[@id="power_power_quiescent_period"]]').text
        self.assertEqual(error_text, u'Please enter a value')

        # Non int value
        b.find_element_by_name('power_quiescent_period').clear()
        b.find_element_by_name('power_quiescent_period').send_keys('nonint')
        b.find_element_by_xpath("//form[@id='power']").submit()
        error_text = b.find_element_by_xpath('//span[@class="help-block error"'
            ' and preceding-sibling::'
            'input[@id="power_power_quiescent_period"]]').text
        self.assertEqual(error_text, u'Please enter an integer value')

    def test_add_power_with_blank_address(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc, with_power=False)
        b = self.browser
        login(b)
        self.go_to_system_view(system)
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//'
            'a[text()="Power Config"]').click()
        Select(b.find_element_by_name('power_type_id'))\
            .select_by_visible_text('ilo')
        self.assertEqual(b.find_element_by_name('power_address').text, '')
        b.find_element_by_xpath("//form[@id='power']").submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            'Saved Power')

    def test_update_power(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//'
            'a[text()="Power Config"]').click()
        b.find_element_by_name('power_address').clear()
        b.find_element_by_name('power_address').send_keys('nowhere.example.com')

        b.find_element_by_name('power_user').clear()
        b.find_element_by_name('power_user').send_keys('asdf')

        b.find_element_by_name('power_passwd').clear()
        b.find_element_by_name('power_passwd').send_keys('meh')

        b.find_element_by_name('power_quiescent_period').clear()
        b.find_element_by_name('power_quiescent_period').send_keys('66')

        b.find_element_by_xpath('//label[normalize-space(string(.))="LeaveOn"]'
                '/input[@type="radio"]').click()

        old_address = self.system.power.power_address
        old_quiescent = self.system.power.power_quiescent_period
        b.find_element_by_xpath("//form[@id='power']").submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            'Updated Power')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)
            self.assertEqual(self.system.power.power_quiescent_period, 66)
            self.assertEqual(self.system.power.power_address,
                'nowhere.example.com')
            self.assertEqual(self.system.power.power_user, 'asdf')
            self.assertEqual(self.system.power.power_passwd, 'meh')
            self.assertEqual(self.system.release_action,
                    ReleaseAction.leave_on)

            activities_to_find = ['power_address', 'power_quiescent_period',
                'power_passwd', 'power_user', 'release_action']
            for activity in self.system.activity:
                if activity.field_name == 'power_passwd':
                    # Can't actually test what the activity entry is
                    activities_to_find.remove(activity.field_name)
                if activity.field_name == 'power_user':
                    # Can't actually test what the activity entry is
                    activities_to_find.remove(activity.field_name)
                if activity.field_name == 'power_address':
                    activities_to_find.remove(activity.field_name)
                    self.assertEqual(activity.old_value, old_address)
                    self.assertEqual(activity.new_value, 'nowhere.example.com')
                if activity.field_name == 'power_quiescent_period':
                    activities_to_find.remove(activity.field_name)
                    self.assertEqual(activity.old_value, str(5))
                    self.assertEqual(activity.new_value, str(66))
                if activity.field_name == 'release_action':
                    activities_to_find.remove(activity.field_name)
                    self.assertEqual(activity.old_value, 'None')
                    self.assertEqual(activity.new_value, 'LeaveOn')
            if activities_to_find:
                raise AssertionError('Could not find activity entries for %s' % ' '.join(activities_to_find))

    def test_add_install_options(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Install Options"]').click()
        b.find_element_by_name('prov_ksmeta').send_keys('skipx asdflol')
        b.find_element_by_name('prov_koptions').send_keys('init=/bin/true')
        b.find_element_by_name('prov_koptionspost').send_keys('vga=0x31b')
        b.find_element_by_name('installoptions').submit()
        b.find_element_by_xpath('//h1[text()="%s"]' % self.system.fqdn)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_delete_install_options(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Install Options"]').click()
        delete_and_confirm(b, '//tr[th/text()="Architecture"]')
        b.find_element_by_xpath('//h1[text()="%s"]' % self.system.fqdn)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)
            self.assert_(self.distro_tree.arch not in self.system.provisions)
            self.assertEquals(self.system.activity[0].action, u'Removed')
            self.assertEquals(self.system.activity[0].field_name,
                    u'InstallOption:kernel_options_post:i386')
            self.assertEquals(self.system.activity[1].action, u'Removed')
            self.assertEquals(self.system.activity[1].field_name,
                    u'InstallOption:kernel_options:i386')
            self.assertEquals(self.system.activity[2].action, u'Removed')
            self.assertEquals(self.system.activity[2].field_name,
                    u'InstallOption:ks_meta:i386')

    def test_update_labinfo(self):
        with session.begin():
            # Due to bz987313 system must have existing lab info
            self.system.labinfo = LabInfo(weight=100)
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]//a[text()="Lab Info"]').click()
        changes = {
            'orig_cost': '1,000.00',
            'curr_cost': '500.00',
            'dimensions': '1x1x1',
            'weight': '50',
            'wattage': '500',
            'cooling': '1',
        }
        for k, v in changes.iteritems():
            b.find_element_by_name(k).clear()
            b.find_element_by_name(k).send_keys(v)
        b.find_element_by_xpath('//button[text()="Save Lab Info Changes"]').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Saved Lab Info')
        for k, v in changes.iteritems():
            self.assertEquals(b.find_element_by_name(k).get_attribute('value'), v)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_owner(self):
        with session.begin():
            new_owner = data_setup.create_user()
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath( # '(Change)' link inside cell beside 'Owner' cell
                '//div[normalize-space(label/text())="Owner"]'
                '//a[normalize-space(string(.))="Change"]').click()
        b.find_element_by_id('Owner_user').send_keys(new_owner.user_name)
        b.find_element_by_id('Owner').submit()
        b.find_element_by_xpath('//h1[text()="%s"]' % self.system.fqdn)
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.owner, new_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691796
    def test_cannot_set_owner_to_none(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath( # '(Change)' link inside cell beside 'Owner' cell
                '//div[normalize-space(label/text())="Owner"]'
                '//a[normalize-space(string(.))="Change"]').click()
        b.find_element_by_id('Owner_user').clear()
        b.find_element_by_id('Owner').submit()
        b.find_element_by_xpath(
                '//span[@class="fielderror" and text()="Please enter a value"]')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.owner, self.system_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=664482
    def test_cannot_change_lab_controller_while_system_in_use(self):
        with session.begin():
            self.system.reserve_manually(service=u'testdata',
                                         user=data_setup.create_user())
        b = self.browser
        login(b)
        self.go_to_system_edit()
        Select(b.find_element_by_name('lab_controller_id'))\
            .select_by_visible_text('None')
        b.find_element_by_link_text('Save Changes').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Unable to change lab controller while system is in use '
                '(return the system first)')
        self.assert_system_view_text('lab_controller_id', self.lab_controller.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=714974
    def test_change_hypervisor(self):
        b = self.browser
        login(b)
        self.go_to_system_edit()
        Select(b.find_element_by_name('hypervisor_id')).select_by_visible_text('KVM')
        b.find_element_by_link_text('Save Changes').click()
        self.assert_system_view_text('hypervisor_id', 'KVM')
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.hypervisor, Hypervisor.by_name(u'KVM'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=749441
    def test_mac_address_with_unicode(self):
        bad_mac_address = u'aяяяяяяяяяяяяяяяяя'
        b = self.browser
        login(b)
        self.go_to_system_edit()
        b.find_element_by_name('mac_address').clear()
        b.find_element_by_name('mac_address').send_keys(bad_mac_address)
        b.find_element_by_link_text('Save Changes').click()
        self.assert_system_view_text('mac_address', bad_mac_address)
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.mac_address, bad_mac_address)

    #https://bugzilla.redhat.com/show_bug.cgi?id=833275
    def test_excluded_families(self):
        # Uses the default distro tree which goes by the name
        # of DansAwesomeLinux created in setUp()

        # append the x86_64 architecture to the system
        self.system.arch.append(Arch.by_name(u'x86_64'))

        # set up the distro tree for x86_64
        with session.begin():
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64')
            self.system.provisions[distro_tree.arch] = Provision(arch=distro_tree.arch)

        self.go_to_system_view(self.system)
        b = self.browser

        # go to the Excluded Families Tab
        b.find_element_by_xpath('//ul[@class="nav nav-tabs"]'
                '//a[text()="Excluded Families"]').click()

        # simulate the label click for i386
        b.find_element_by_xpath('//li[normalize-space(text())="i386"]'
                  '//label[normalize-space(string(.))="DansAwesomeLinux6.9"]').click()
        # Now check if the appropriate checkbox was selected
        self.assertTrue(b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.i386" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).is_selected())
        self.assertFalse(b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.x86_64" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).is_selected())

        # Uncheck the i386 checkbox
        b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.i386" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).click()

        # simulate the label click for x86_64
        b.find_element_by_xpath('//li[normalize-space(text())="x86_64"]'
                  '//label[normalize-space(string(.))="DansAwesomeLinux6.9"]').click()
        # Now check if the appropriate checkbox was selected
        self.assertTrue(b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.x86_64" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).is_selected())
        self.assertFalse(b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.i386" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).is_selected())

class SystemCcTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            user = data_setup.create_user(password=u'swordfish')
            self.system = data_setup.create_system(owner=user)
        self.browser = self.get_browser()
        login(self.browser, user=user.user_name, password='swordfish')

    def tearDown(self):
        self.browser.quit()

    def test_add_email_addresses(self):
        with session.begin():
            self.system.cc = []
        b = self.browser
        b.get(get_server_base() + 'cc_change?system_id=%s' % self.system.id)
        b.find_element_by_id('cc_cc_0_email_address').send_keys('roy.baty@pkd.com')
        b.find_element_by_id('doclink').click()
        b.find_element_by_id('cc_cc_1_email_address').send_keys('deckard@police.gov')
        b.find_element_by_xpath('//input[@value="Change"]').click()
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(set(self.system.cc),
                    set([u'roy.baty@pkd.com', u'deckard@police.gov']))
            activity = self.system.activity[-1]
            self.assertEquals(activity.field_name, u'Cc')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Changed')
            self.assertEquals(activity.old_value, u'')
            self.assertEquals(activity.new_value,
                    u'roy.baty@pkd.com; deckard@police.gov')

    def test_remove_email_addresses(self):
        with session.begin():
            self.system.cc = [u'roy.baty@pkd.com', u'deckard@police.gov']
        b = self.browser
        b.get(get_server_base() + 'cc_change?system_id=%s' % self.system.id)
        b.find_element_by_xpath('//tr[@id="cc_cc_1"]//a[text()="Remove (-)"]').click()
        # The tg_expanding_widget javascript doesn't let us remove the last element,
        # so we have to just clear it instead :-S
        b.find_element_by_id('cc_cc_0_email_address').clear()
        b.find_element_by_xpath('//input[@value="Change"]').click()
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.cc, [])
            activity = self.system.activity[-1]
            self.assertEquals(activity.field_name, u'Cc')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Changed')
            self.assertEquals(activity.old_value,
                    u'deckard@police.gov; roy.baty@pkd.com')
            self.assertEquals(activity.new_value, u'')

    def test_replace_existing_email_address(self):
        with session.begin():
            self.system.cc = [u'roy.baty@pkd.com']
        b = self.browser
        b.get(get_server_base() + 'cc_change?system_id=%s' % self.system.id)
        b.find_element_by_id('cc_cc_0_email_address').clear()
        b.find_element_by_id('cc_cc_0_email_address').send_keys('deckard@police.gov')
        b.find_element_by_xpath('//input[@value="Change"]').click()
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.cc, [u'deckard@police.gov'])
            activity = self.system.activity[-1]
            self.assertEquals(activity.field_name, u'Cc')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Changed')
            self.assertEquals(activity.old_value, u'roy.baty@pkd.com')
            self.assertEquals(activity.new_value, u'deckard@police.gov')

class TestSystemViewRDF(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)

    def test_turtle(self):
        rdf_url = urljoin(get_server_base(),
                'view/%s?%s' % (quote(self.system.fqdn.encode('utf8')),
                    urlencode({'tg_format': 'turtle'})))
        graph = rdflib.graph.Graph()
        graph.parse(location=rdf_url, format='n3')
        self.assert_(len(graph) >= 9)

    def test_rdfxml(self):
        rdf_url = urljoin(get_server_base(),
                'view/%s?%s' % (quote(self.system.fqdn.encode('utf8')),
                    urlencode({'tg_format': 'rdfxml'})))
        graph = rdflib.graph.Graph()
        graph.parse(location=rdf_url, format='xml')
        self.assert_(len(graph) >= 9)
