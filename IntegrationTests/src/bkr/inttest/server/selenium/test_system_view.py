
# vim: set fileencoding=utf-8:

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import logging
import time
from urlparse import urljoin
from urllib import urlencode, quote
import requests
import rdflib.graph
from turbogears.database import session

from bkr.inttest import data_setup, get_server_base, \
        assertions, with_transaction, DatabaseTestCase
from bkr.server.model import Arch, Key, Key_Value_String, Key_Value_Int, System, \
        Provision, ProvisionFamily, ProvisionFamilyUpdate, Hypervisor, \
        SystemStatus, LabInfo, ReleaseAction, PowerType, SystemPool, RecipeTask
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, check_system_search_results, \
        delete_and_confirm, logout, click_menu_item, BootstrapSelect, wait_for_ajax_loading
from bkr.inttest.server.requests_utils import login as requests_login, patch_json
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import ElementNotVisibleException
from bkr.inttest.assertions import wait_for_condition, assert_sorted

class SystemViewTestWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.system_owner = data_setup.create_user()
            self.unprivileged_user = data_setup.create_user(password=u'password')
            self.system = data_setup.create_system(lab_controller=self.lab_controller,
                    owner=self.system_owner, status=SystemStatus.automated, arch=u'i386')
            self.distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[self.lab_controller])
        self.browser = self.get_browser()

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
        self.go_to_system_view(tab='Scheduler Settings')
        self.assertFalse(b.find_element_by_name('status_reason').is_enabled())
        with session.begin():
            self.system.status = SystemStatus.broken
        self.go_to_system_view(tab='Scheduler Settings')
        self.assertTrue(b.find_element_by_name('status_reason').is_enabled())

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
        modal.find_element_by_xpath('.//button[contains(text(), "Rename")]')
        # check errors don't stack up
        # https://bugzilla.redhat.com/show_bug.cgi?id=1161373
        modal.find_element_by_tag_name('form').submit()
        modal.find_element_by_xpath('.//button[contains(text(), "Rename")]')
        errors = modal.find_elements_by_class_name('alert-error')
        self.assertEquals(len(errors), 1, 'Multiple errors: %r' % errors)

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

    def test_submit_inventory_job(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Details')
        tab = b.find_element_by_id('details')
        tab.find_element_by_xpath('.//button[normalize-space(string(.))="Scan"]').click()
        tab.find_element_by_xpath('.//button[normalize-space(string(.))="Scan" and @disabled="disabled"]')
        with session.begin():
            session.refresh(self.system)
            recipe = self.system.find_current_hardware_scan_recipe()
            recipe_id, status = recipe.id, recipe.status
        self.assertIn('Hardware scan in progress: R:%s (%s)' % (recipe_id, status),
                      tab.find_element_by_xpath('//div[contains(@class, "hardware-scan-status")]').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1364311
    def test_scan_status_link_works(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Details')
        tab = b.find_element_by_id('details')
        tab.find_element_by_xpath('.//button[normalize-space(string(.))="Scan"]').click()
        tab.find_element_by_xpath('.//button[normalize-space(string(.))="Scan" and @disabled="disabled"]')
        with session.begin():
            session.refresh(self.system)
            recipe_id = self.system.find_current_hardware_scan_recipe().id

        tab.find_element_by_xpath('//div[contains(@class, "hardware-scan-status")]/a').click()
        b.find_element_by_xpath('//title[contains(.,"R:%s")]' % recipe_id)

    def test_change_status(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Scheduler Settings')
        tab = b.find_element_by_id('scheduler-settings')
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
        self.go_to_system_view(tab='Scheduler Settings')
        tab = b.find_element_by_id('scheduler-settings')
        BootstrapSelect(tab.find_element_by_name('status'))\
            .select_by_visible_text('Broken')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        b.find_element_by_xpath('//span[@class="label label-warning"'
                ' and text()="Out of service"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=980352
    def test_condition_report_too_long(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Scheduler Settings')
        tab = b.find_element_by_id('scheduler-settings')
        BootstrapSelect(tab.find_element_by_name('status'))\
            .select_by_visible_text('Broken')
        # The browser should prevent us from typing in more than 4000 
        # characters. We populate the first 3999 characters using 
        # execute_script because sending each key individually is too slow.
        # https://code.google.com/p/selenium/issues/detail?id=3732#c8
        b.execute_script('document.getElementById("status_reason").value = "%s"'
                % ('a' * 3999))
        b.find_element_by_name('status_reason').send_keys('bbbbb')
        value = b.find_element_by_name('status_reason').get_attribute('value')
        self.assertEqual(len(value), 4000)

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

        # should be rejected server-side also
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % self.system.fqdn,
                session=s, data=dict(fqdn=u'lol...?'))
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text, u'Invalid FQDN for system: lol...?')

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

        # should be rejected server-side also
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % self.system.fqdn,
                session=s, data=dict(fqdn=u'löööööl'))
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text, u'Invalid FQDN for system: löööööl')

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

    def test_add_pool(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            orig_date_modified = system.date_modified
        # as admin, assign the system to our test pool
        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_name('pool').send_keys(pool.name)
        b.find_element_by_class_name('system-pool-add').submit()
        self.assertEquals(b.find_element_by_xpath('//div[@id="list-system-pools"]'
                                                  '/ul[@class="list-group system-pools-list"]'
                                                  '/li/a').text, pool.name)
        with session.begin():
            session.refresh(system)
            self.assert_(system.date_modified > orig_date_modified)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1364311
    def test_link_to_pools_works(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            system.pools.append(pool)
        # as admin, assign the system to our test pool
        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_xpath('//div[@id="list-system-pools"]'
                                '/ul[@class="list-group system-pools-list"]'
                                '/li/a').click()
        b.find_element_by_xpath('//title[normalize-space(text())="%s"]' % pool.name)

    def test_add_nonexistent_pool(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Pools')
        b.find_element_by_name('pool').send_keys('rockpool')
        b.find_element_by_class_name('system-pool-add').submit()
        # confirmation modal should appear
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Pool does not exist. Create it?"]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        b.find_element_by_xpath('//ul[@class="list-group system-pools-list"]'
                '/li[a/text()="rockpool"]')
        with session.begin():
            session.expire_all()
            pool = SystemPool.by_name(u'rockpool')
            self.assertIn(pool, self.system.pools)

    def test_remove_pool(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            system.pools.append(pool)
            orig_date_modified = system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_link_text(pool.name)
        # remove
        b.find_element_by_xpath('//li[contains(a/text(), "%s")]/button' % pool.name).click()
        b.find_element_by_xpath('//div[@id="list-system-pools" and '
                                'not(./ul/li)]')
        with session.begin():
            session.refresh(system)
            self.assert_(system.date_modified > orig_date_modified)

        # A pool owner or an user with edit permissions on a system can remove a system from a pool
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system(owner=user)
            system.pools.append(pool)
        logout(b)
        login(b, user=user.user_name, password='password')
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_link_text(pool.name)
        # remove
        b.find_element_by_xpath('//li[contains(a/text(), "%s")]/button' % pool.name).click()
        b.find_element_by_xpath('//div[@id="list-system-pools" and '
                                'not(./ul/li)]')
        with session.begin():
            session.refresh(system)
            self.assertNotIn(pool, system.pools)

    # https://bugzilla.redhat.com/show_bug.cgi?id=917745
    def test_add_pool_to_system_twice(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            orig_date_modified = self.system.date_modified
        # as admin, assign the system to our test pool
        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_name('pool').send_keys(pool.name)
        b.find_element_by_class_name('system-pool-add').submit()
        self.assertEquals(b.find_element_by_xpath('//div[@id="list-system-pools"]'
                                                  '/ul[@class="list-group system-pools-list"]'
                                                  '/li/a').text, pool.name)
        with session.begin():
            session.refresh(system)
            self.assert_(system.date_modified > orig_date_modified)

        orig_date_modified = system.date_modified
        # add again
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_name('pool').send_keys(pool.name)
        b.find_element_by_class_name('system-pool-add').submit()
        # this is a no-op, will just clear the input field
        self.assertFalse(b.find_element_by_name('pool').text)
        with session.begin():
            session.refresh(system)
            self.assert_(system.date_modified == orig_date_modified)

    def test_remove_pool_updates_active_access_policy(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            system.pools.append(pool)
            system.active_access_policy = pool.access_policy

        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Access Policy')
        self.assertTrue(b.find_element_by_xpath(
            '//label[contains(string(.), "Use policy from pool:")]'
            '/input[@type="radio"]').is_selected())
        # remove from pool
        self.go_to_system_view(system=system, tab='Pools')
        b.find_element_by_link_text(pool.name)
        b.find_element_by_xpath('//li[contains(a/text(), "%s")]/button' % pool.name).click()
        b.find_element_by_xpath('//div[@id="list-system-pools" and '
                                'not(./ul/li)]')

        # check for the active access policy
        self.go_to_system_view(system=system, tab='Access Policy')
        # The system should be set to using its custom access policy
        self.assertTrue(b.find_element_by_xpath(
            '//label[contains(string(.), "Use custom access policy")]'
            '/input[@type="radio"]').is_selected())

    def test_unprivileged_user_cannot_see_power_settings(self):
        with session.begin():
            self.system.power.power_passwd = u'midnight'
        b = self.browser
        login(b, self.unprivileged_user.user_name, 'password')
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        self.assertEquals(tab.find_element_by_class_name('alert-info').text,
                'You do not have permission to view power configuration '
                'for this system.')
        self.assertNotIn('midnight', tab.text)

    def test_power_quiescent_default_value(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc, with_power=False)
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        period = tab.find_element_by_name('power_quiescent_period').get_attribute('value')
        self.assertEqual(period, str(5))

    def test_update_power_invalid_quiescent_period(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        # Empty value
        tab.find_element_by_name('power_quiescent_period').clear()
        tab.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error
        tab.find_element_by_css_selector('input[name=power_quiescent_period]:invalid')

        # Non int value
        tab.find_element_by_name('power_quiescent_period').send_keys('nonint')
        tab.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error
        tab.find_element_by_css_selector('input[name=power_quiescent_period]:invalid')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1070561
    # https://bugzilla.redhat.com/show_bug.cgi?id=1152887
    def test_add_power_with_blank_address(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc, with_power=False)
        b = self.browser
        login(b)
        self.go_to_system_view(system, tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        BootstrapSelect(tab.find_element_by_name('power_type'))\
            .select_by_visible_text('ilo')
        self.assertEqual(
                tab.find_element_by_name('power_address').get_attribute('value'),
                '')
        tab.find_element_by_tag_name('form').submit()
        # we can't actually check the HTML5 validation error
        tab.find_element_by_css_selector('input[name=power_address]:invalid')

    def test_update_power(self):
        orig_date_modified = self.system.date_modified
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        tab.find_element_by_name('power_address').clear()
        tab.find_element_by_name('power_address').send_keys('nowhere.example.com')

        tab.find_element_by_name('power_user').clear()
        tab.find_element_by_name('power_user').send_keys('asdf')

        tab.find_element_by_name('power_password').clear()
        tab.find_element_by_name('power_password').send_keys('meh')

        tab.find_element_by_name('power_quiescent_period').clear()
        tab.find_element_by_name('power_quiescent_period').send_keys('66')

        b.find_element_by_xpath('//label[normalize-space(string(.))="LeaveOn"]'
                '/input[@type="radio"]').click()

        old_address = self.system.power.power_address
        old_quiescent = self.system.power.power_quiescent_period
        tab.find_element_by_tag_name('form').submit()
        tab.find_element_by_xpath('.//button[text()="Save Changes"]')
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
                    self.assertEqual(activity.old_value, 'PowerOff')
                    self.assertEqual(activity.new_value, 'LeaveOn')
            if activities_to_find:
                raise AssertionError('Could not find activity entries for %s' % ' '.join(activities_to_find))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1209736
    def test_power_settings_with_closing_script_tag(self):
        bad_value = u'lols</script>HAX'
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        tab.find_element_by_name('power_password').clear()
        tab.find_element_by_name('power_password').send_keys(bad_value)
        tab.find_element_by_tag_name('form').submit()
        # wait for changes to save
        tab.find_element_by_xpath('.//button[text()="Save Changes"]')
        # re-open the page and make sure it renders properly
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        self.assertEquals(
                tab.find_element_by_name('power_password').get_attribute('value'),
                bad_value)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1145867
    def test_new_power_settings(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc, 
                                              with_power=False)

        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        BootstrapSelect(tab.find_element_by_name('power_type'))\
            .select_by_visible_text('virsh')
        tab.find_element_by_name('power_address').send_keys \
            ('qemu+ssh:10.10.10.10')
        tab.find_element_by_name('power_user').send_keys('root')
        tab.find_element_by_name('power_id').send_keys(system.fqdn)
        tab.find_element_by_tag_name('form').submit()
        tab.find_element_by_xpath('.//button[text()="Save Changes"]')

        # check activity records
        power_fields_changed = {'power_type': 'virsh',
                                'power_address': 'qemu+ssh:10.10.10.10',
                                'power_user': '********',
                                'power_passwd': '********',
                                'power_id': system.fqdn,
                                'power_quiescent_period': '5'}
        with session.begin():
            session.refresh(system)
            self.assertEquals(len(system.activity), len(power_fields_changed.keys()))
            for activity in system.activity:
                self.assertEquals(activity.new_value,
                                  power_fields_changed[activity.field_name])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1386074
    def test_new_power_settings_saved_twice(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    with_power=False)
        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        BootstrapSelect(tab.find_element_by_name('power_type'))\
            .select_by_visible_text('ilo')
        tab.find_element_by_name('power_address').send_keys('nowhere')
        tab.find_element_by_tag_name('form').submit()
        # Wait for request to complete
        tab.find_element_by_xpath('.//button[text()="Save Changes"]')
        # Change power settings and save them again
        tab.find_element_by_name('power_address').clear()
        tab.find_element_by_name('power_address').send_keys('somewhere')
        tab.find_element_by_tag_name('form').submit()
        # Wait for request to complete
        tab.find_element_by_xpath('.//button[text()="Save Changes"]')
        # There should be no error div
        tab.find_element_by_xpath('.//div[@class="sync-status" and '
                'not(.//div[contains(@class, "alert")])]')
        # Database should be updated
        with session.begin():
            #session.refresh(system.power)
            self.assertEqual(system.power.power_address, u'somewhere')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1059535
    def test_activity_is_not_logged_when_leaving_power_settings_empty(self):
        # The bug was that we were recording a change to power_user or 
        # power_passwd because it changed from NULL to ''.
        with session.begin():
            self.system.power.power_type = PowerType.lazy_create(name=u'ilo')
            self.system.power.power_user = None
            self.system.power.power_passwd = None
            self.system.power.power_id = None
            PowerType.lazy_create(name=u'drac')
            self.assertEquals(len(self.system.activity), 0)
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Power Settings')
        tab = b.find_element_by_id('power-settings')
        # change power type but leave the other fields empty
        BootstrapSelect(tab.find_element_by_name('power_type'))\
            .select_by_visible_text('drac')
        tab.find_element_by_tag_name('form').submit()
        tab.find_element_by_xpath('.//button[text()="Save Changes"]')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(len(self.system.activity), 1,
                    'Expecting only one activity row for power_type but found: %r'
                    % self.system.activity)
            self.assertEquals(self.system.activity[0].field_name, u'power_type')

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

    def test_cannot_set_owner_to_invalid_user(self):
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Owner')
        tab = b.find_element_by_id('owner')
        tab.find_element_by_xpath('.//button[contains(text(), "Change")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').send_keys('$!7676')
        modal.find_element_by_tag_name('form').submit()
        self.assertIn(
            'No such user', 
            modal.find_element_by_class_name('alert-error').text)
        modal.find_element_by_xpath('.//button[contains(text(), "Save changes")]')
        # check errors don't stack up
        # https://bugzilla.redhat.com/show_bug.cgi?id=1161373
        modal.find_element_by_tag_name('form').submit()
        modal.find_element_by_xpath('.//button[contains(text(), "Save changes")]')
        errors = modal.find_elements_by_class_name('alert-error')
        self.assertEquals(len(errors), 1, 'Multiple errors: %r' % errors)

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
            system = data_setup.create_system(lab_controller=self.lab_controller,
                                              status=SystemStatus.manual)
            system.reserve_manually(service=u'testdata',
                                    user=data_setup.create_user())
        b = self.browser
        login(b)
        self.go_to_system_view(system=system, tab='Essentials')
        tab = b.find_element_by_id('essentials')
        BootstrapSelect(b.find_element_by_name('lab_controller_id'))\
            .select_by_visible_text('(none)')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        self.assertIn(
                'Unable to change lab controller while system is in use '
                '(return the system first)',
                tab.find_element_by_class_name('alert-error').text)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1309059
    def test_removed_lab_controllers_are_not_visible(self):
        with session.begin():
            lab_controller = data_setup.create_labcontroller()
            lab_controller.removed = datetime.datetime.utcnow()
        b = self.browser
        login(b)
        self.go_to_system_view(tab='Essentials')
        tab = b.find_element_by_id('essentials')
        options = BootstrapSelect(b.find_element_by_name('lab_controller_id')).options
        self.assertNotIn(lab_controller.fqdn, options)

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
    def test_exclude_by_architecture(self):
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
        # click the major version to open the submenu, wait for it to open, and then click the osversion
        b.find_element_by_xpath('//div[@id="arch-i386"]//i[@data-target="#collapse-i386-DansAwesomeLinux6"]').click()
        time.sleep(0.42)
        b.find_element_by_xpath('//div[@id="arch-i386"]//span[text()="DansAwesomeLinux6.9"]').click()

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

        # Change the tab and simulate the label click for x86_64
        b.find_element_by_id('x86_64-tab').click()
        b.find_element_by_xpath('//div[@id="arch-x86_64"]//i[@data-target="#collapse-x86_64-DansAwesomeLinux6"]').click()
        time.sleep(0.42)
        b.find_element_by_xpath('//div[@id="arch-x86_64"]//span[text()="DansAwesomeLinux6.9"]').click()

        # Now check if the appropriate checkbox was selected
        self.assertTrue(b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.x86_64" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).is_selected())
        self.assertFalse(b.find_element_by_xpath(
                '//input[@name="excluded_families_subsection.i386" and @value="%s"]'
                % self.distro_tree.distro.osversion_id).is_selected())

    def test_exclude_all(self):
        #view excluded families
        b = self.browser
        login(b)
        #navigate to the correct tabs
        self.go_to_system_view(tab='Excluded Families')
        tab = b.find_element_by_id('exclude')
        #simulate click of exclude all button
        tab.find_element_by_id('excludeButton').click()
        #find all major rel checkboxes
        checkboxes = b.find_elements_by_class_name('majorCheckbox')
        #assert all clicks are correct
        assert all([i.is_selected() for i in checkboxes])

    def test_exclude_filter(self):
        # Creates more distro trees to apply the filter on
        with session.begin():
            distro_names = [u'RenansAwesomeLinux3', u'AnyOtherLinux0']
            for distro_name in distro_names:
                data_setup.create_distro_tree(osmajor=distro_name, osminor=u'2', lab_controllers=[self.lab_controller])
        self.go_to_system_view(tab='Excluded Families')
        b = self.browser

        # type a string in the filter input field
        input_filter = b.find_element_by_css_selector('div.filter input').send_keys('awe')
        # check if the matching majors are being shown
        b.find_element_by_xpath('//div[@id="arch-i386"]//i[@data-target="#collapse-i386-DansAwesomeLinux6"]').click()
        b.find_element_by_xpath('//div[@id="arch-i386"]//i[@data-target="#collapse-i386-RenansAwesomeLinux3"]').click()
        # check if the non-matching majors are not being shown
        try:
            b.find_element_by_xpath('//div[@id="arch-i386"]//i[@data-target="#collapse-i386-AnyOtherLinux0"]').click()
        except ElementNotVisibleException:
            return
        self.fail('Element is displayed but it should not.')

    def test_can_sort_activity_grid(self):
        with session.begin():
            self.system.record_activity(service=u'testdata', field=u'status_reason',
                    new=u'aaa')
            self.system.record_activity(service=u'testdata', field=u'status_reason',
                    new=u'bbb')
            self.system.record_activity(service=u'testdata', field=u'status_reason',
                    new=u'ccc')
        b = self.browser
        login(b)
        self.go_to_system_view(self.system, tab=u'Activity')
        tab = b.find_element_by_id('history')
        table = tab.find_element_by_tag_name('table')
        column = 7 # New Value
        # by default the grid is sorted by id descending
        cell_values = [table.find_element_by_xpath('tbody/tr[%d]/td[%d]'
                % (row, column)).text for row in [1, 2, 3]]
        self.assertEquals(cell_values, ['ccc', 'bbb', 'aaa'])
        # sort by New Value column
        table.find_element_by_xpath('thead/tr/th[%d]/a[text()="New Value"]' % column).click()
        # wait for the sort indicator in the column header to appear
        table.find_element_by_xpath('thead/tr/th[%d][contains(@class, "ascending")]' % column)
        # wait for the data loading indicator to disappear
        wait_for_ajax_loading(b, 'loading-overlay')
        cell_values = [table.find_element_by_xpath('tbody/tr[%d]/td[%d]'
                % (row, column)).text for row in [1, 2, 3]]
        self.assertEquals(cell_values, ['aaa', 'bbb', 'ccc'])

    def test_can_filter_activity_grid(self):
        with session.begin():
            self.system.record_activity(service=u'testdata', field=u'status_reason',
                    new=u'Simon says')
            self.system.record_activity(service=u'testdata', field=u'status_reason',
                    new=u'Archer says')
        b = self.browser
        login(b)
        self.go_to_system_view(self.system, tab=u'Activity')
        tab = b.find_element_by_id('history')
        tab.find_element_by_xpath('.//input[@type="search"]')\
            .send_keys('"Simon says"\n')
        tab.find_element_by_xpath('.//table[contains(@class, "table") and '
                'not(.//td[7]/text()="Archer says") and '
                './/td[7]/text()="Simon says"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1122464
    def test_can_sort_executed_tasks_grid(self):
        self.browser = self.get_browser()
        with session.begin():
            job1 = data_setup.create_completed_job(system=self.system)
            job2 = data_setup.create_completed_job(system=self.system)
            job3 = data_setup.create_running_job(system=self.system)
        b = self.browser
        login(b)
        self.go_to_system_view(self.system, tab=u'Executed Tasks')
        tab = b.find_element_by_id('tasks')
        table = tab.find_element_by_tag_name('table')
        column = 1 # Run ID
        # by default the grid is sorted by id descending
        cell_values = [table.find_element_by_xpath('tbody/tr[%d]/td[%d]/a' %
                                                   (row, column)).text for row in [1, 2, 3]]
        self.assertEquals(cell_values, [job3.recipesets[0].recipes[0].tasks[0].t_id,
                                        job2.recipesets[0].recipes[0].tasks[0].t_id,
                                        job1.recipesets[0].recipes[0].tasks[0].t_id])
        # sort by Run ID column
        table.find_element_by_xpath('thead/tr/th[%d]/a[text()="Run ID"]' % column).click()
        # wait for the sort indicator in the column header to appear
        table.find_element_by_xpath('thead/tr/th[%d][contains(@class, "ascending")]' % column)
        # wait for the data loading indicator to disappear
        wait_for_ajax_loading(b, 'loading-overlay')
        cell_values = [table.find_element_by_xpath('tbody/tr[%d]/td[%d]/a' %
                                                   (row, column)).text for row in [1, 2, 3]]
        self.assertEquals(cell_values, [job1.recipesets[0].recipes[0].tasks[0].t_id,
                                        job2.recipesets[0].recipes[0].tasks[0].t_id,
                                        job3.recipesets[0].recipes[0].tasks[0].t_id])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1122464
    def test_can_filter_executed_tasks_grid(self):
        with session.begin():
            data_setup.create_completed_job(system=self.system,
                                            distro_tree=self.distro_tree)
            dt = data_setup.create_distro_tree()
            data_setup.create_completed_job(system=self.system,
                                            distro_tree=dt)
        b = self.browser
        login(b)
        self.go_to_system_view(self.system, tab=u'Executed Tasks')
        tab = b.find_element_by_id('tasks')
        tab.find_element_by_xpath('.//input[@type="search"]')\
            .send_keys('"%s"\n' % self.distro_tree.distro.name)
        tab.find_element_by_xpath('.//table[contains(@class, "table") and '
                'not(.//td[3]/a[contains(text(), "%s")]) and '
                './/td[3]/a[contains(text(), "%s")]]' % (dt.distro.name, self.distro_tree.distro.name))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1232979
    def test_external_task_name_on_executed_tasks_grid(self):
        with session.begin():
            recipe = data_setup.create_recipe(task_name=u'/distribution/check-install')
            external_task = RecipeTask.from_fetch_url(url='git://example.com/externaltasks/example#master',
                                        subdir='examples')
            recipe.tasks.extend([external_task])
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_running(recipe, system=self.system)
        b = self.browser
        login(b)
        self.go_to_system_view(self.system, tab=u'Executed Tasks')
        tab = b.find_element_by_id('tasks')
        tab.find_element_by_xpath('.//table[contains(@class, "table") and '
                'normalize-space(.//td[2]/text())="%s"]' % external_task.name)

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
                '/button[contains(text(), "Remove")]').click()
        tab.find_element_by_xpath('.//ul[not(./li[contains(text(), "roy.baty@pkd.com")])]')
        tab.find_element_by_xpath('.//li[contains(text(), "deckard@police.gov")]'
                '/button[contains(text(), "Remove")]').click()
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

class TestSystemViewRDF(DatabaseTestCase):

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

class SystemStatusHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by bkr system-status.
    """

    def test_it(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=data_setup.create_labcontroller(),
                                              status=SystemStatus.manual)
            reserved_by = data_setup.create_user(u'dracula')
            loaned_to = data_setup.create_user(u'wolfman')
            system.reserve_manually(user=reserved_by, service=u'testdata')
            system.loaned = loaned_to
            system.loan_comment = u'For evil purposes'
        response = requests.get(get_server_base() + 'systems/%s/status' % system.fqdn)
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['condition'], 'Manual')
        reservation_info = json['current_reservation']
        self.assertEquals(reservation_info['user_name'], u'dracula') # Beaker 0.15.3
        self.assertEquals(reservation_info['user']['user_name'], 'dracula') # Beaker 19
        loan_info = json['current_loan']
        self.assertEquals(loan_info['recipient'], u'wolfman') # Beaker 0.15.3
        self.assertEquals(loan_info['recipient_user']['user_name'], 'wolfman') # Beaker 19
        self.assertEquals(loan_info['comment'], u'For evil purposes')

class SystemActivityHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for system activity.
    """

    # https://bugzilla.redhat.com/show_bug.cgi?id=1193746
    def test_enforced_pagination_redirect(self):
        with session.begin():
            system = data_setup.create_system()
            # need >500 activity rows to trigger forced pagination
            for _ in xrange(501):
                system.record_activity(service=u'testdata',
                        field=u'nonsense', action=u'poke')
        original_url = (get_server_base() +
                'systems/%s/activity/?q=action:poke' % system.fqdn)
        expected_redirect = (get_server_base() +
                'systems/%s/activity/?q=action:poke&page_size=20' % system.fqdn)
        response = requests.get(original_url, allow_redirects=False,
                headers={'Accept': 'application/json'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers['Location'], expected_redirect)
        # For completeness, the same thing with no query params.
        original_url = (get_server_base() +
                'systems/%s/activity/' % system.fqdn)
        expected_redirect = (get_server_base() +
                'systems/%s/activity/?page_size=20' % system.fqdn)
        response = requests.get(original_url, allow_redirects=False,
                headers={'Accept': 'application/json'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers['Location'], expected_redirect)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1401964
    def test_filter_by_activity_id_range(self):
        with session.begin():
            system = data_setup.create_system()
            excluded_activity = system.record_activity(service=u'testdata',
                    field=u'nonsense', action=u'fire')
            included_activity = system.record_activity(service=u'testdata',
                    field=u'nonsense', action=u'fire')
        url = (get_server_base() +
                'systems/%s/activity/?q=id:[%s TO *]' %
                (system.fqdn, included_activity.id))
        response = requests.get(url, allow_redirects=False,
                headers={'Accept': 'application/json'})
        results = [activity['id'] for activity in response.json()['entries']]
        self.assertIn(included_activity.id, results)
        self.assertNotIn(excluded_activity.id, results)
