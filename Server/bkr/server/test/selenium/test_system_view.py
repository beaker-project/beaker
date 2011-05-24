
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

from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup, get_server_base, stub_cobbler, \
        assertions
from bkr.server.model import Key, Key_Value_String, Key_Value_Int, System, \
        Provision

class SystemViewTest(SeleniumTestCase):

    def setUp(self):
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.stub_cobbler_thread.start()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        self.system_owner = data_setup.create_user()
        self.unprivileged_user = data_setup.create_user(password=u'password')
        self.distro = data_setup.create_distro()
        self.system = data_setup.create_system(owner=self.system_owner,
                status=u'Automated')
        self.system.shared = True
        self.system.provisions[self.distro.arch] = Provision(
                arch=self.distro.arch, ks_meta=u'some_ks_meta_var',
                kernel_options=u'some_kernel_option=1',
                kernel_options_post=u'some_kernel_option=2')
        self.system.lab_controller = self.lab_controller
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()
        self.stub_cobbler_thread.stop()

    def go_to_system_view(self):
        sel = self.selenium
        sel.open('')
        sel.type('simplesearch', self.system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.assertEquals(self.selenium.get_title(), self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=623603
    # see also TestRecipeView.test_can_report_problem
    def test_can_report_problem(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('link=(Report problem)')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(self.selenium.get_title(),
                'Report a problem with %s' % self.system.fqdn)

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

    def test_update_system(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
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
            self.assertEquals(sel.get_value(k), v)
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_status(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.select('status_id', u'Broken')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_selected_label('status_id'), u'Broken')
        session.clear()
        self.system = System.query().get(self.system.id)
        self.assertEqual(self.system.status.status, u'Broken')
        self.assertEqual(len(self.system.status_durations), 2)
        self.assertEqual(self.system.status_durations[0].status.status,
                u'Broken')
        assertions.assert_datetime_within(
                self.system.status_durations[0].start_time,
                tolerance=datetime.timedelta(seconds=60),
                reference=datetime.datetime.utcnow())
        self.assert_(self.system.status_durations[0].finish_time is None)
        self.assert_(self.system.status_durations[1].finish_time is not None)
        assertions.assert_durations_not_overlapping(
                self.system.status_durations)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_strips_surrounding_whitespace_from_fqdn(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.type('fqdn', '    lol    ')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_value('fqdn'), 'lol')

    def test_rejects_malformed_fqdn(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.type('fqdn', 'lol...?')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.fielderror'),
                'The supplied value is not a valid hostname')

    def test_rejects_non_ascii_chars_in_fqdn(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.type('fqdn', u'lööööl')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.fielderror'),
                'The supplied value is not a valid hostname')

    # https://bugzilla.redhat.com/show_bug.cgi?id=683003
    def test_forces_fqdn_to_lowercase(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.type('fqdn', 'LooOOooL')
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_value('fqdn'), 'looooool')

    # https://bugzilla.redhat.com/show_bug.cgi?id=670912
    def test_renaming_system_removes_from_cobbler(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        old_fqdn = self.system.fqdn
        new_fqdn = 'commodore64.example.com'
        sel.type('fqdn', new_fqdn)
        sel.click('link=Save Changes')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_value('fqdn'), new_fqdn)
        self.assert_(old_fqdn in self.stub_cobbler_thread.cobbler.removed_systems)

    def test_add_arch(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Arch(s)"]')
        sel.type('arch.text', 's390')
        sel.click('//form[@name="arches"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_xpath_count('//form[@name="arches"]'
                '//td[normalize-space(text())="s390"]'), 1)
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
        self.assertEquals(sel.get_xpath_count('//form[@name="arches"]'
                '//td[normalize-space(text())="i386"]'), 1)
        sel.click( # delete link inside cell beside "i386" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::td[1]/text())="i386"]'
                '/a[text()="Delete ( - )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'i386 Removed')
        self.assertEquals(sel.get_xpath_count('//form[@name="arches"]'
                '//td[normalize-space(text())="i386"]'), 0)
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
        self.assertEquals(sel.get_xpath_count('//form[@name="keys"]'
                '//td[normalize-space(preceding-sibling::td[1]/text())="NR_DISKS" and '
                'normalize-space(text())="100"]'), 1)
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_remove_key_value(self):
        self.system.key_values_int.append(
                Key_Value_Int(Key.by_name(u'NR_DISKS'), 100))
        session.flush()
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Key/Values"]')
        self.assertEquals(sel.get_xpath_count('//form[@name="keys"]'
                '//td[normalize-space(preceding-sibling::td[1]/text())="NR_DISKS" and '
                'normalize-space(text())="100"]'), 1)
        sel.click( # delete link inside cell in row with NR_DISKS 100
                '//table[@class="list"]//td['
                'normalize-space(preceding-sibling::td[2]/text())="NR_DISKS" and '
                'normalize-space(preceding-sibling::td[1]/text())="100"'
                ']/a[text()="Delete ( - )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'removed NR_DISKS/100')
        self.assertEquals(sel.get_xpath_count('//form[@name="keys"]'
                '//td[normalize-space(preceding-sibling::td[1]/text())="NR_DISKS" and '
                'normalize-space(text())="100"]'), 0)
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_add_group(self):
        group = data_setup.create_group()
        user_password = 'password'
        user = data_setup.create_user(password=user_password)
        data_setup.add_user_to_group(user, group)
        session.flush()
        orig_date_modified = self.system.date_modified

        # as admin, assign the system to our test group
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Groups"]')
        sel.type("groups_group_text", group.group_name)
        sel.click('//form[@name="groups"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load("30000")
        self.assertEquals(sel.get_xpath_count('//form[@name="groups"]'
                '//td[normalize-space(text())="%s"]' % group.group_name), 1)
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
        group = data_setup.create_group()
        self.system.groups.append(group)
        session.flush()
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Groups"]')
        self.assertEquals(sel.get_xpath_count('//form[@name="groups"]'
                '//td[normalize-space(text())="%s"]' % group.group_name), 1)
        sel.click( # delete link inside cell in row with group name
                '//table[@class="list"]'
                '//td[normalize-space(preceding-sibling::td[3]/text())="%s"]'
                '/a[text()="Delete ( - )"]' % group.group_name)
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'),
                '%s Removed' % group.display_name)
        self.assertEquals(sel.get_xpath_count('//form[@name="groups"]'
                '//td[normalize-space(text())="%s"]' % group.group_name), 0)
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
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

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
            self.assertEquals(sel.get_value(k), v)
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_change_owner(self):
        new_owner = data_setup.create_user()
        session.flush()
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
        self.assertEquals(sel.get_title(), 'Systems')
        self.assertEquals(sel.get_text('css=.flash'), 'OK')
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
        session.refresh(self.system)
        self.assertEquals(self.system.owner, self.system_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=706150
    def test_install_options_populated_on_provision_tab(self):
        self.login(self.unprivileged_user.user_name, 'password')
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Provision"]')
        sel.select('prov_install', self.distro.install_name)
        self.wait_and_try(self.check_install_options)

    def check_install_options(self):
        sel = self.selenium
        self.assertEqual(sel.get_value('ks_meta'), 'some_ks_meta_var')
        self.assertEqual(sel.get_value('koptions'), 'some_kernel_option=1')
        self.assertEqual(sel.get_value('koptions_post'), 'some_kernel_option=2')

    # https://bugzilla.redhat.com/show_bug.cgi?id=703548
    def test_cc_not_visible_to_random_noobs(self):
        self.login(self.unprivileged_user.user_name, 'password')
        sel = self.selenium
        self.go_to_system_view()
        self.assert_(not sel.is_text_present('Notify CC'))

class SystemCcTest(SeleniumTestCase):

    def setUp(self):
        user = data_setup.create_user(password=u'swordfish')
        self.system = data_setup.create_system(owner=user)
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login(user=user.user_name, password='swordfish')

    def tearDown(self):
        self.selenium.stop()

    def test_add_email_addresses(self):
        self.system.cc = []
        session.flush()
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        assert not sel.get_value('cc_cc_0_email_address'), 'should be empty'
        sel.type('cc_cc_0_email_address', 'roy.baty@pkd.com')
        sel.click('doclink') # why the hell is it called this?
        sel.type('cc_cc_1_email_address', 'deckard@police.gov')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
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
        self.system.cc = [u'roy.baty@pkd.com', u'deckard@police.gov']
        session.flush()
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.click('//tr[@id="cc_cc_1"]//a[text()="Remove (-)"]')
        #sel.click('//tr[@id="cc_cc_0"]//a[text()="Remove (-)"]')
        # The tg_expanding_widget javascript doesn't let us remove the last element,
        # so we have to just clear it instead :-S
        sel.type('cc_cc_0_email_address', '')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
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
        self.system.cc = [u'roy.baty@pkd.com']
        session.flush()
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.type('cc_cc_0_email_address', 'deckard@police.gov')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
        session.refresh(self.system)
        self.assertEquals(self.system.cc, [u'deckard@police.gov'])
        activity = self.system.activity[-1]
        self.assertEquals(activity.field_name, u'Cc')
        self.assertEquals(activity.service, u'WEBUI')
        self.assertEquals(activity.action, u'Changed')
        self.assertEquals(activity.old_value, u'roy.baty@pkd.com')
        self.assertEquals(activity.new_value, u'deckard@police.gov')

class TestSystemViewRDF(unittest.TestCase):

    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)
        session.flush()

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
