
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

from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, get_server_base, \
        assertions, with_transaction
from bkr.server.model import Key, Key_Value_String, Key_Value_Int, System, \
        Provision, ProvisionFamily, ProvisionFamilyUpdate, Hypervisor, \
        SystemStatus
from bkr.server.tools import beakerd


class SystemViewTest(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.lab_controller = data_setup.create_labcontroller()
        self.system_owner = data_setup.create_user()
        self.unprivileged_user = data_setup.create_user(password=u'password')
        self.distro_tree = data_setup.create_distro_tree()
        self.system = data_setup.create_system(owner=self.system_owner,
                status=u'Automated', arch=u'i386')
        self.system.shared = True
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
        self.system.lab_controller = self.lab_controller
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()


    def go_to_system_edit(self, system=None):
        if system is None:
            system = self.system
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('30000')
        sel.type('simplesearch', system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        sel.click('link=%s' % system.fqdn)
        sel.wait_for_page_to_load('30000')
        sel.click('link=Edit System')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), system.fqdn)

    def go_to_system_view(self, system=None):
        if system is None:
            system = self.system
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('30000')
        sel.type('simplesearch', system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        sel.click('link=%s' % system.fqdn)
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), system.fqdn)

    def test_system_view_condition_report(self):
        sel = self.selenium
        self.login()
        self.go_to_system_view()
        is_hidden = sel.get_xpath_count("//tr[@id='condition_report_row' and @class='list hidden']")
        self.assert_(is_hidden == 1)
        with session.begin():
            self.system.status = SystemStatus.broken
        self.go_to_system_view()
        not_hidden = sel.get_xpath_count("//tr[@id='condition_report_row' and @class='list']")
        self.assert_(not_hidden == 1)

    def test_current_job(self):
        sel = self.selenium
        self.login()
        with session.begin():
            job = data_setup.create_job(owner=self.system.owner,
                    distro_tree=self.distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % self.system.fqdn)
            job_id = job.id
        beakerd.new_recipes()
        beakerd.processed_recipesets()
        beakerd.queued_recipes()
        self.go_to_system_view()
        sel.click('link=(Current Job)')
        sel.wait_for_page_to_load('30000')
        self.assert_('J:%s' % job_id in sel.get_title())

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.assertEquals(self.selenium.get_title(), self.system.fqdn)

    def test_links_to_cc_change(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click( # link inside cell beside "Notify CC" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::th[1]/label/text())="Notify CC"]'
                '/a[text()="(Change)"]')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(self.selenium.get_title(),
                'Notify CC list for %s' % self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=747086
    def test_update_system_no_lc(self):
        with session.begin():
            system = data_setup.create_system()
            system.labcontroller = None
        self.login()
        sel = self.selenium
        self.go_to_system_edit(system=system)
        new_fqdn = 'zx81.example.com'
        sel.type('fqdn', new_fqdn)
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assert_system_view_text('fqdn', new_fqdn)

    def test_update_system(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        changes = {
            'fqdn': 'zx80.example.com',
            'vendor': 'Sinclair',
            'model': 'ZX80',
            'serial': '12345',
            'mac_address': 'aa:bb:cc:dd:ee:ff',
        }
        for k, v in changes.iteritems():
            sel.type(k, v)
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        for k, v in changes.iteritems():
            self.assert_system_view_text(k, v)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_status(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.select('status', u'Broken')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
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
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        self.go_to_system_edit()
        sel.select('status', u'Broken')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), self.system.fqdn)
        self.assert_system_view_text('status', u'Broken')

    def test_strips_surrounding_whitespace_from_fqdn(self):
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.type('fqdn', '    lol    ')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assert_system_view_text('fqdn', 'lol')

    def test_rejects_malformed_fqdn(self):
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.type('fqdn', 'lol...?')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.fielderror'),
                'The supplied value is not a valid hostname')

    def test_rejects_non_ascii_chars_in_fqdn(self):
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.type('fqdn', u'lööööl')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.fielderror'),
                'The supplied value is not a valid hostname')

    # https://bugzilla.redhat.com/show_bug.cgi?id=683003
    def test_forces_fqdn_to_lowercase(self):
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.type('fqdn', 'LooOOooL')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assert_system_view_text('fqdn', 'looooool')

    def test_add_arch(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Arch(s)"]')
        sel.type('arch.text', 's390')
        sel.click('//form[@name="arches"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_xpath_count(
                '//div[normalize-space(@class)="tabbertab"]'
                '//td[normalize-space(text())="s390"]'), 1)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    # https://bugzilla.redhat.com/show_bug.cgi?id=677951
    def test_add_nonexistent_arch(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Arch(s)"]')
        sel.type('arch.text', 'notexist')
        sel.click('//form[@name="arches"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), u'No such arch notexist')

    def test_remove_arch(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Arch(s)"]')
        self.assertEquals(sel.get_xpath_count(
                '//div[normalize-space(@class)="tabbertab"]'
                '//td[normalize-space(text())="i386"]'), 1)
        sel.click( # delete link inside cell beside "i386" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::td[1]/text())="i386"]'
                '//a[text()="Delete ( - )"]')
        sel.click("//button[@type='button' and text()='Yes']")
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'i386 Removed')
        self.assertEquals(sel.get_xpath_count(
                '//div[normalize-space(@class)="tabbertab"]'
                '//td[normalize-space(text())="i386"]'), 0)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_add_key_value(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Key/Values"]')
        sel.type('key_name', 'NR_DISKS')
        sel.type('key_value', '100')
        sel.click('//form[@name="keys"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_xpath_count(
                '//td[normalize-space(preceding-sibling::td[1]/text())'
                '="NR_DISKS" and '
                'normalize-space(text())="100"]'), 1)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_remove_key_value(self):
        with session.begin():
            self.system.key_values_int.append(
                    Key_Value_Int(Key.by_name(u'NR_DISKS'), 100))
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Key/Values"]')
        self.assertEquals(sel.get_xpath_count(
                '//td[normalize-space(preceding-sibling::td[1]/text())'
                '="NR_DISKS" and '
                'normalize-space(text())="100"]'), 1)
        sel.click( # delete link inside cell in row with NR_DISKS 100
                '//table[@class="list"]//td['
                'normalize-space(preceding-sibling::td[2]/text())="NR_DISKS" and '
                'normalize-space(preceding-sibling::td[1]/text())="100"'
                ']//a[text()="Delete ( - )"]')
        sel.click("//button[@type='button' and text()='Yes']")
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'removed NR_DISKS/100')
        self.assertEquals(sel.get_xpath_count(
                '//td[normalize-space(preceding-sibling::td[1]/text())'
                '="NR_DISKS" and '
                'normalize-space(text())="100"]'), 0)
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
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Groups"]')
        sel.type("groups_group_text", group.group_name)
        sel.click('//form[@name="groups"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load("30000")
        self.assertEquals(sel.get_xpath_count(
                '//div[normalize-space(@class)="tabbertab"]'
                '//td[normalize-space(text())="%s"]' % group.group_name), 1)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

        # as a user in the group, can we see it?
        self.logout()
        self.login(user.user_name, user_password)
        sel.click("link=Available")
        sel.wait_for_page_to_load("30000")
        sel.type('simplesearch', self.system.fqdn)
        sel.submit('systemsearch_simple')
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present(self.system.fqdn))

    def test_remove_group(self):
        with session.begin():
            group = data_setup.create_group()
            self.system.groups.append(group)
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Groups"]')
        self.assertEquals(sel.get_xpath_count(
                '//td[normalize-space(text())="%s"]' % group.group_name), 1)
        sel.click( # delete link inside cell in row with group name
                '//table[@class="list"]'
                '//td[normalize-space(preceding-sibling::td[3]/text())="%s"]'
                '//a[text()="Delete ( - )"]' % group.group_name)
        sel.click("//button[@type='button' and text()='Yes']")
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'),
                '%s Removed' % group.display_name)
        self.assertEquals(sel.get_xpath_count(
                '//td[normalize-space(text())="%s"]' % group.group_name), 0)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_update_power(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Power"]')
        sel.select('name=power_type_id', 'drac')
        sel.type('name=power_address', 'nowhere.example.com')
        sel.type('name=power_user', 'asdf')
        sel.type('name=power_passwd', 'meh')
        sel.type('name=power_id', '1234')
        sel.click('link=Save Power Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Updated Power')
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_add_install_options(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Install Options"]')
        sel.type('prov_ksmeta', 'skipx asdflol')
        sel.type('prov_koptions', 'init=/bin/true')
        sel.type('prov_koptionspost', 'vga=0x31b')
        sel.click('//form[@name="installoptions"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), self.system.fqdn)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_delete_install_options(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Install Options"]')
        sel.click('//tr[th/text()="Architecture"]'
                '//a[text()="Delete ( - )"]')
        sel.click("//button[@type='button' and text()='Yes']")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), self.system.fqdn)
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
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Lab Info"]')
        changes = {
            'orig_cost': '1,000.00',
            'curr_cost': '500.00',
            'dimensions': '1x1x1',
            'weight': '50',
            'wattage': '500',
            'cooling': '1',
        }
        for k, v in changes.iteritems():
            sel.type(k, v)
        sel.click('link=Save Lab Info Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Saved Lab Info')
        for k, v in changes.iteritems():
            self.assertEqual(sel.get_value(k), v)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_owner(self):
        with session.begin():
            new_owner = data_setup.create_user()
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click( # '(Change)' link inside cell beside 'Owner' cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::th[1]/label/text())="Owner"]'
                '/a[normalize-space(span/text())="(Change)"]')
        sel.wait_for_page_to_load('30000')
        sel.type('Owner_user', new_owner.user_name)
        sel.submit('Owner')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_title(), self.system.fqdn)
        self.assertEquals(sel.get_text('css=.flash'), 'OK')
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.owner, new_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691796
    def test_cannot_set_owner_to_none(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click( # '(Change)' link inside cell beside 'Owner' cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::th[1]/label/text())="Owner"]'
                '/a[normalize-space(span/text())="(Change)"]')
        sel.wait_for_page_to_load('30000')
        sel.type('Owner_user', '')
        sel.submit('Owner')
        sel.wait_for_page_to_load('30000')
        self.assert_(sel.get_title().startswith('Change Owner'), sel.get_title())
        self.assert_(sel.is_element_present(
                '//span[@class="fielderror" and text()="Please enter a value"]'))
        with session.begin():
            session.refresh(self.system)
            self.assertEquals(self.system.owner, self.system_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=706150
    def test_install_options_populated_on_provision_tab(self):
        self.login(self.unprivileged_user.user_name, 'password')
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Provision"]')
        sel.select('prov_install', unicode(self.distro_tree))
        self.wait_and_try(self.check_install_options)

    def check_install_options(self):
        sel = self.selenium
        self.assertEqual(sel.get_value('ks_meta'), 'some_ks_meta_var=3')
        # noverifyssl comes from server-test.cfg
        self.assertEqual(sel.get_value('koptions'), 'noverifyssl some_kernel_option=5')
        self.assertEqual(sel.get_value('koptions_post'), 'some_kernel_option=6')

    # https://bugzilla.redhat.com/show_bug.cgi?id=703548
    def test_cc_not_visible_to_random_noobs(self):
        self.login(self.unprivileged_user.user_name, 'password')
        sel = self.selenium
        self.go_to_system_view()
        self.assert_(not sel.is_text_present('Notify CC'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=664482
    def test_cannot_change_lab_controller_while_system_in_use(self):
        with session.begin():
            self.system.reserve(service=u'testdata', reservation_type=u'manual',
                    user=data_setup.create_user())
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.select('lab_controller_id', 'None')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'),
                'Unable to change lab controller while system is in use '
                '(return the system first)')
        self.assert_system_view_text('lab_controller_id', self.lab_controller.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=714974
    def test_change_hypervisor(self):
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.select('hypervisor_id', 'KVM')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assert_system_view_text('hypervisor_id', 'KVM')
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.hypervisor, Hypervisor.by_name(u'KVM'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=749441
    def test_mac_address_with_unicode(self):
        bad_mac_address = u'aяяяяяяяяяяяяяяяяя'
        self.login()
        sel = self.selenium
        self.go_to_system_edit()
        sel.type('mac_address', bad_mac_address)
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assert_system_view_text('mac_address', bad_mac_address)
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.mac_address, bad_mac_address)

    # https://bugzilla.redhat.com/show_bug.cgi?id=740321
    def test_no_power_without_lc(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        self.assert_(sel.is_element_present(
                '//input[@value="Power On System"]'))
        self.go_to_system_edit()
        sel.select('lab_controller_id', 'None')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assert_(sel.is_element_present(
                '//span[text()="System is not configured for power support"]'))

class SystemCcTest(SeleniumTestCase):

    def setUp(self):
        with session.begin():
            user = data_setup.create_user(password=u'swordfish')
            self.system = data_setup.create_system(owner=user)
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login(user=user.user_name, password='swordfish')

    def tearDown(self):
        self.selenium.stop()

    def test_add_email_addresses(self):
        with session.begin():
            self.system.cc = []
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.wait_for_page_to_load('30000')
        assert not sel.get_value('cc_cc_0_email_address'), 'should be empty'
        sel.type('cc_cc_0_email_address', 'roy.baty@pkd.com')
        sel.click('doclink') # why the hell is it called this?
        sel.type('cc_cc_1_email_address', 'deckard@police.gov')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
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
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.wait_for_page_to_load('30000')
        sel.click('//tr[@id="cc_cc_1"]//a[text()="Remove (-)"]')
        #sel.click('//tr[@id="cc_cc_0"]//a[text()="Remove (-)"]')
        # The tg_expanding_widget javascript doesn't let us remove the last element,
        # so we have to just clear it instead :-S
        sel.type('cc_cc_0_email_address', '')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
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
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.wait_for_page_to_load('30000')
        sel.type('cc_cc_0_email_address', 'deckard@police.gov')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
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
