
# vim: set fileencoding=utf-8:

# Beaker
#
# Copyright (C) 2010 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

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
        SystemStatus, LabInfo
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, check_system_search_results, \
        delete_and_confirm, logout, click_menu_item, BootstrapSelect
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
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=987313
    def test_labinfo_not_visible_for_new_systems(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath('//ul[contains(@class, "system-nav") and '
                'not(.//a/text()="Lab Info")]')

    def go_to_system_view(self, system=None, tab=None):
        if system is None:
            system = self.system
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_xpath('//title[normalize-space(text())="%s"]' % \
            system.fqdn)
        if tab:
            b.find_element_by_xpath('//ul[contains(@class, "system-nav")]'
                    '//a[text()="%s"]' % tab).click()

    def test_system_view_condition_report(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Scheduler')
        self.assertFalse(b.find_element_by_name('status_reason').is_enabled())
        with session.begin():
            self.system.status = SystemStatus.broken
        self.go_to_system_view(tab='Scheduler')
        self.assertTrue(b.find_element_by_name('status_reason').is_enabled())

    def test_current_job(self):
        b = self.browser
        login(b)
        with session.begin():
            job = data_setup.create_job(owner=self.system.owner,
                    distro_tree=self.distro_tree)
            data_setup.mark_job_running(job, system=self.system)
            recipe = job.recipesets[0].recipes[0]
        self.go_to_system_view()
        usage = b.find_element_by_class_name('system-quick-usage')
        usage.find_element_by_xpath('//span[@class="label" and text()="Reserved"]')
        usage.find_element_by_xpath('//a[text()="%s"]' % recipe.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.browser.find_element_by_xpath('//title[text()="%s"]' % self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=747086
    def test_rename_system_no_lc(self):
        with session.begin():
            self.system.labcontroller = None
        b = self.browser
        login(b)
        self.go_to_system_view()
        new_fqdn = 'zx81.example.com'
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys(new_fqdn)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//h1[contains(text(), "%s")]' % new_fqdn)

    def test_rename_system(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        new_fqdn = 'zx80.example.com'
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys(new_fqdn)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//h1[contains(text(), "%s")]' % new_fqdn)

    def test_rename_system_duplicate(self):
        existing_fqdn = u'existingsystem.test-system-view'
        with session.begin():
            data_setup.create_system(fqdn=existing_fqdn)
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys(existing_fqdn)
        modal.find_element_by_tag_name('form').submit()
        self.assertIn('already exists',
                modal.find_element_by_class_name('alert-error').text)

    def test_update_system(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Details')
        tab = b.find_element_by_id('details')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        changes = {
            'vendor': 'Sinclair',
            'model': 'ZX80',
            'serial_number': '12345',
            'mac_address': 'aa:bb:cc:dd:ee:ff',
        }
        for k, v in changes.iteritems():
            modal.find_element_by_name(k).clear()
            modal.find_element_by_name(k).send_keys(v)
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        tab.find_element_by_xpath('.//tr[th/text()="Vendor" and td/text()="Sinclair"]')
        tab.find_element_by_xpath('.//tr[th/text()="Model" and td/text()="ZX80"]')
        tab.find_element_by_xpath('.//tr[th/text()="Serial Number" and td/text()="12345"]')
        tab.find_element_by_xpath('.//tr[th/text()="MAC Address" and td/text()="aa:bb:cc:dd:ee:ff"]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_status(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Scheduler')
        tab = b.find_element_by_id('scheduler')
        BootstrapSelect(tab.find_element_by_name('status'))\
            .select_by_visible_text('Broken')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        b.find_element_by_xpath('//span[@class="label label-warning"'
                ' and text()="Out of service"]')
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
        self.go_to_system_view(tab='Scheduler')
        tab = b.find_element_by_id('scheduler')
        BootstrapSelect(tab.find_element_by_name('status'))\
            .select_by_visible_text('Broken')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        b.find_element_by_xpath('//span[@class="label label-warning"'
                ' and text()="Out of service"]')

    def test_rejects_fqdn_with_whitespace(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys('   lol   ')
        modal.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error,
        # but we should still be at the system rename modal
        modal.find_element_by_css_selector('input[name=fqdn]:invalid')

    def test_rejects_malformed_fqdn(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys('lol...?')
        modal.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error,
        # but we should still be at the system rename modal
        modal.find_element_by_css_selector('input[name=fqdn]:invalid')

    def test_rejects_non_ascii_chars_in_fqdn(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys(u'lööööl')
        modal.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error,
        # but we should still be at the system rename modal
        modal.find_element_by_css_selector('input[name=fqdn]:invalid')

    # https://bugzilla.redhat.com/show_bug.cgi?id=683003
    def test_forces_fqdn_to_lowercase(self):
        b = self.browser
        login(b)
        self.go_to_system_view()
        b.find_element_by_xpath('//h1/button[contains(text(), "Rename")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('fqdn').clear()
        modal.find_element_by_name('fqdn').send_keys('LooOOool')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//h1[contains(text(), "looooool")]')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.fqdn, u'looooool')

    def test_add_arch(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Essentials')
        tab = b.find_element_by_id('essentials')
        BootstrapSelect(tab.find_element_by_name('arches'))\
            .select_by_visible_text('s390')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        b.find_element_by_xpath('//div[@id="essentials"]//span[@class="sync-status" and not(text())]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_remove_arch(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Essentials')
        tab = b.find_element_by_id('essentials')
        BootstrapSelect(tab.find_element_by_name('arches'))\
            .select_by_visible_text('i386') # actually deselecting
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        b.find_element_by_xpath('//div[@id="essentials"]//span[@class="sync-status" and not(text())]')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_add_key_value(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Key/Values')
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
        self.go_to_system_view(tab='Key/Values')
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
        self.go_to_system_view(tab='Groups')
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
        self.go_to_system_view(tab='Groups')
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

    def test_update_power_quiescent_validator(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power')
        # Empty value
        b.find_element_by_name('power_quiescent_period').clear()
        b.find_element_by_xpath("//form[@id='power']").submit()
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

    def test_update_power(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power')
        b.find_element_by_name('power_address').clear()
        b.find_element_by_name('power_address').send_keys('nowhere.example.com')

        b.find_element_by_name('power_user').clear()
        b.find_element_by_name('power_user').send_keys('asdf')

        b.find_element_by_name('power_passwd').clear()
        b.find_element_by_name('power_passwd').send_keys('meh')

        b.find_element_by_name('power_quiescent_period').clear()
        b.find_element_by_name('power_quiescent_period').send_keys('66')

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

            activities_to_find = ['power_address', 'power_quiescent_period',
                'power_passwd', 'power_user']
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
            if activities_to_find:
                raise AssertionError('Could not find activity entries for %s' % ' '.join(activities_to_find))


    def test_add_install_options(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Install Options')
        b.find_element_by_name('prov_ksmeta').send_keys('skipx asdflol')
        b.find_element_by_name('prov_koptions').send_keys('init=/bin/true')
        b.find_element_by_name('prov_koptionspost').send_keys('vga=0x31b')
        b.find_element_by_name('installoptions').submit()
        b.find_element_by_xpath('//h1[text()="%s"]' % self.system.fqdn)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_delete_install_options(self):
        with session.begin():
            self.system.provisions[self.distro_tree.arch] = Provision(
                    arch=self.distro_tree.arch, ks_meta=u'some_ks_meta_var=1',
                    kernel_options=u'some_kernel_option=1',
                    kernel_options_post=u'some_kernel_option=2')
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Install Options')
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
        self.go_to_system_view(tab='Lab Info')
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
        self.go_to_system_view(tab='Owner')
        tab = b.find_element_by_id('owner')
        tab.find_element_by_xpath('.//button[contains(text(), "Change")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').send_keys(new_owner.user_name)
        modal.find_element_by_tag_name('form').submit()
        tab.find_element_by_xpath('p[1]/a[text()="%s"]' % new_owner.user_name)
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.owner, new_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691796
    def test_cannot_set_owner_to_none(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Owner')
        tab = b.find_element_by_id('owner')
        tab.find_element_by_xpath('.//button[contains(text(), "Change")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').clear()
        modal.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error,
        # but we should still be at the system modal
        modal.find_element_by_css_selector('input[name=user_name]:required')
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
        self.go_to_system_view(tab='Essentials')
        tab = b.find_element_by_id('essentials')
        BootstrapSelect(b.find_element_by_name('lab_controller_id'))\
            .select_by_visible_text('(none)')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        self.assertIn(
                'Unable to change lab controller while system is in use '
                '(return the system first)',
                tab.find_element_by_class_name('alert-error').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=714974
    def test_change_hypervisor(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Details')
        tab = b.find_element_by_id('details')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        Select(modal.find_element_by_name('hypervisor'))\
            .select_by_visible_text('KVM')
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        tab.find_element_by_xpath('.//tr[th/text()="Host Hypervisor" and td/text()="KVM"]')
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.hypervisor, Hypervisor.by_name(u'KVM'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=749441
    def test_mac_address_with_unicode(self):
        bad_mac_address = u'aяяяяяяяяяяяяяяяяя'
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Details')
        tab = b.find_element_by_id('details')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('mac_address').clear()
        modal.find_element_by_name('mac_address').send_keys(bad_mac_address)
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        tab.find_element_by_xpath('.//tr[th/text()="MAC Address" and td/text()="%s"]'
                % bad_mac_address)
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

        self.go_to_system_view(tab='Excluded Families')
        b = self.browser

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

    def test_add_cc(self):
        with session.begin():
            self.system.cc = []
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Owner')
        tab = b.find_element_by_id('owner')
        tab.find_element_by_name('cc').send_keys('roy.baty@pkd.com')
        tab.find_element_by_class_name('cc-add').submit()
        tab.find_element_by_xpath('.//li[contains(text(), "roy.baty@pkd.com")]')
        tab.find_element_by_name('cc').send_keys('deckard@police.gov')
        tab.find_element_by_class_name('cc-add').submit()
        tab.find_element_by_xpath('.//li[contains(text(), "deckard@police.gov")]')
        tab.find_element_by_xpath('.//li[contains(text(), "roy.baty@pkd.com")]')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(set(self.system.cc),
                    set([u'roy.baty@pkd.com', u'deckard@police.gov']))
            self.assertEquals(self.system.activity[0].field_name, u'Cc')
            self.assertEquals(self.system.activity[0].service, u'HTTP')
            self.assertEquals(self.system.activity[0].action, u'Added')
            self.assertEquals(self.system.activity[0].new_value, u'deckard@police.gov')
            self.assertEquals(self.system.activity[1].field_name, u'Cc')
            self.assertEquals(self.system.activity[1].service, u'HTTP')
            self.assertEquals(self.system.activity[1].action, u'Added')
            self.assertEquals(self.system.activity[1].new_value, u'roy.baty@pkd.com')

    def test_remove_cc(self):
        with session.begin():
            self.system.cc = [u'roy.baty@pkd.com', u'deckard@police.gov']
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Owner')
        tab = b.find_element_by_id('owner')
        tab.find_element_by_xpath('.//li[contains(text(), "roy.baty@pkd.com")]'
                '/a[@title="Remove"]').click()
        tab.find_element_by_xpath('.//ul[not(./li[contains(text(), "roy.baty@pkd.com")])]')
        tab.find_element_by_xpath('.//li[contains(text(), "deckard@police.gov")]'
                '/a[@title="Remove"]').click()
        tab.find_element_by_xpath('.//ul[not(./li[contains(text(), "deckard@police.gov")])]')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.cc, [])
            self.assertEquals(self.system.activity[0].field_name, u'Cc')
            self.assertEquals(self.system.activity[0].service, u'HTTP')
            self.assertEquals(self.system.activity[0].action, u'Removed')
            self.assertEquals(self.system.activity[0].old_value, u'deckard@police.gov')
            self.assertEquals(self.system.activity[1].field_name, u'Cc')
            self.assertEquals(self.system.activity[1].service, u'HTTP')
            self.assertEquals(self.system.activity[1].action, u'Removed')
            self.assertEquals(self.system.activity[1].old_value, u'roy.baty@pkd.com')

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
