# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
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
import logging
from urlparse import urljoin
from urllib import urlencode, urlopen, quote
import lxml.etree
import xmlrpclib
import rdflib.graph
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.server.test import data_setup, get_server_base, stub_cobbler
from bkr.server.test.assertions import assert_sorted
from bkr.server.model import User, Cpu, Key, Key_Value_String, Key_Value_Int

def atom_xpath(expr):
    return lxml.etree.XPath(expr, namespaces={'atom': 'http://www.w3.org/2005/Atom'})

class TestSystemsGrid(SeleniumTestCase):

    def setUp(self):
        data_setup.create_system()
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_atom_feed_link_is_present(self):
        sel = self.selenium
        sel.open('')
        self.assertEqual(sel.get_xpath_count('/html/head/link[@rel="feed" '
                'and @title="Atom feed" and contains(@href, "tg_format=atom")]'),
                '1')

class TestSystemGridSorting(SeleniumTestCase):

    # tests in this class can safely share the same firefox session
    @classmethod
    def setUpClass(cls):
        try:
            session.begin()
            # ensure we have lots of systems
            for cores in [1, 2, 3]:
                for vendor, model, status, type, user in zip(
                        [u'Acer', u'Dell', u'HP'],
                        [u'slow model', u'fast model', u'big model'],
                        [u'Automated', u'Manual', u'Removed'],
                        [u'Machine', u'Virtual', u'Prototype'],
                        [data_setup.create_user() for _ in range(3)]):
                    system = data_setup.create_system(vendor=vendor,
                            model=model, status=status, type=type)
                    system.user = data_setup.create_user()
                    system.cpu = Cpu(cores=cores)
            session.commit()
        finally:
            session.close()
        cls.selenium = sel = cls.get_selenium()
        sel.start()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.stop()

    # https://bugzilla.redhat.com/show_bug.cgi?id=651418

    def check_column_sort(self, column):
        sel = self.selenium
        try:
            sel.click('link=Show all')
            sel.wait_for_page_to_load('30000')
        except: pass
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        cell_values = [sel.get_table('widget.%d.%d' % (row, column - 1)) # zero-indexed
                       for row in range(0, row_count)]
        self.assert_(len(set(cell_values)) > 1) # make sure we're checking something
        assert_sorted(cell_values, key=lambda x: x.lower())

    # We test both ordinary listing (i.e. with no search query) as well as 
    # searching, because they go through substantially different code paths

    def go_to_listing(self):
        self.selenium.open('')

    def go_to_search_results(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=Toggle Search')
        sel.select('systemsearch_0_table', 'CPU/Cores')
        sel.select('systemsearch_0_operation', 'greater than')
        sel.type('systemsearch_0_value', '1')
        sel.click('//form[@name="systemsearch"]//a[text()="Add ( + )"]')
        sel.select('systemsearch_1_table', 'System/Name')
        sel.select('systemsearch_1_operation', 'is not')
        sel.type('systemsearch_1_value', 'bob')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')

    def test_can_sort_listing_by_status(self):
        self.go_to_listing()
        self.check_column_sort(2)

    def test_can_sort_listing_by_vendor(self):
        self.go_to_listing()
        self.check_column_sort(3)

    def test_can_sort_listing_by_model(self):
        self.go_to_listing()
        self.check_column_sort(4)

    def test_can_sort_listing_by_user(self):
        self.go_to_listing()
        self.check_column_sort(6)

    def test_can_sort_listing_by_type(self):
        self.go_to_listing()
        self.check_column_sort(7)

    def test_can_sort_search_results_by_vendor(self):
        self.go_to_search_results()
        self.check_column_sort(2)

    def test_can_sort_search_results_by_user(self):
        self.go_to_search_results()
        self.check_column_sort(3)

    def test_can_sort_search_results_by_type(self):
        self.go_to_search_results()
        self.check_column_sort(4)

    def test_can_sort_search_results_by_status(self):
        self.go_to_search_results()
        self.check_column_sort(5)

    def test_can_sort_search_results_by_model(self):
        self.go_to_search_results()
        self.check_column_sort(7)

    # XXX also test with custom column selections

class TestSystemsAtomFeed(unittest.TestCase):

    def feed_contains_system(self, feed, fqdn):
        xpath = atom_xpath('/atom:feed/atom:entry/atom:title[text()="%s"]' % fqdn)
        return len(xpath(feed))

    def test_all_systems(self):
        systems = [data_setup.create_system() for _ in range(3)]
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        for system in systems:
            self.assert_(self.feed_contains_system(feed, system.fqdn))

    def test_link_to_rdfxml(self):
        system = data_setup.create_system()
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        href_xpath = atom_xpath(
                '/atom:feed/atom:entry[atom:title/text()="%s"]'
                '/atom:link[@rel="alternate" and @type="application/rdf+xml"]/@href'
                % system.fqdn)
        href, = href_xpath(feed)
        self.assertEqual(href,
                '%sview/%s?tg_format=rdfxml' % (get_server_base(), system.fqdn))

    def test_link_to_turtle(self):
        system = data_setup.create_system()
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        href_xpath = atom_xpath(
                '/atom:feed/atom:entry[atom:title/text()="%s"]'
                '/atom:link[@rel="alternate" and @type="application/x-turtle"]/@href'
                % system.fqdn)
        href, = href_xpath(feed)
        self.assertEqual(href,
                '%sview/%s?tg_format=turtle' % (get_server_base(), system.fqdn))

    def test_filter_by_group(self):
        data_setup.create_system(fqdn=u'nogroup.system')
        self.group = data_setup.create_group()
        data_setup.create_system(fqdn=u'grouped.system').groups.append(self.group)
        session.flush()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'systemsearch-0.table': 'System/Group',
                'systemsearch-0.operation': 'is',
                'systemsearch-0.value': self.group.group_name}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assert_(not self.feed_contains_system(feed, 'nogroup.system'))
        self.assert_(self.feed_contains_system(feed, 'grouped.system'))

class SystemViewTest(SeleniumTestCase):

    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)
        self.system.shared = True
        self.system.lab_controller = data_setup.create_labcontroller()
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def go_to_system_view(self):
        sel = self.selenium
        sel.open('')
        sel.type('simplesearch', self.system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('3000')
        sel.click('link=%s' % self.system.fqdn)
        sel.wait_for_page_to_load('3000')

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
        sel.wait_for_page_to_load('3000')
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
                '//td[normalize-space(text())="s390"]'), '1')
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

    def test_remove_arch(self):
        orig_date_modified = self.system.date_modified
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('//ul[@class="tabbernav"]//a[text()="Arch(s)"]')
        self.assertEquals(sel.get_xpath_count('//form[@name="arches"]'
                '//td[normalize-space(text())="i386"]'), '1')
        sel.click( # delete link inside cell beside "i386" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::td[1]/text())="i386"]'
                '/a[text()="Delete ( - )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'i386 Removed')
        self.assertEquals(sel.get_xpath_count('//form[@name="arches"]'
                '//td[normalize-space(text())="i386"]'), '0')
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
                'normalize-space(text())="100"]'), '1')
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
                'normalize-space(text())="100"]'), '1')
        sel.click( # delete link inside cell in row with NR_DISKS 100
                '//table[@class="list"]//td['
                'normalize-space(preceding-sibling::td[2]/text())="NR_DISKS" and '
                'normalize-space(preceding-sibling::td[1]/text())="100"'
                ']/a[text()="Delete ( - )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'removed NR_DISKS/100')
        self.assertEquals(sel.get_xpath_count('//form[@name="keys"]'
                '//td[normalize-space(preceding-sibling::td[1]/text())="NR_DISKS" and '
                'normalize-space(text())="100"]'), '0')
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
                '//td[normalize-space(text())="%s"]' % group.group_name), '1')
        session.refresh(self.system)
        self.assert_(self.system.date_modified > orig_date_modified)

        # as a user in the group, can we see it?
        self.logout()
        self.login(user.user_name, user_password)
        sel.click("link=Available")
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
                '//td[normalize-space(text())="%s"]' % group.group_name), '1')
        sel.click( # delete link inside cell in row with group name
                '//table[@class="list"]'
                '//td[normalize-space(preceding-sibling::td[3]/text())="%s"]'
                '/a[text()="Delete ( - )"]' % group.group_name)
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'),
                '%s Removed' % group.display_name)
        self.assertEquals(sel.get_xpath_count('//form[@name="groups"]'
                '//td[normalize-space(text())="%s"]' % group.group_name), '0')
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

class ReserveSystemXmlRpcTest(XmlRpcTestCase):

    def test_cannot_reserve_when_not_logged_in(self):
        system = data_setup.create_system()
        session.flush()
        server = self.get_server()
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_(e.faultString.startswith(
                    'cherrypy._cperror.HTTPRedirect'))

    def test_cannot_reserve_automated_system(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('Cannot reserve system with status Automated'
                    in e.faultString)

    def test_cannot_reserve_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(owner=user, status=u'Manual', shared=True)
        system.user = User.by_user_name(data_setup.ADMIN_USER)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_(e.faultString.startswith('bkr.server.bexceptions.BX'))

    def test_reserve_system(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        self.assert_(system.user is None)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
        session.refresh(system)
        self.assertEqual(system.user, user)
        reserved_activity = system.activity[-1]
        self.assertEqual(reserved_activity.action, 'Reserved')
        self.assertEqual(reserved_activity.field_name, 'User')
        self.assertEqual(reserved_activity.user, user)
        self.assertEqual(reserved_activity.new_value, user.user_name)
        self.assertEqual(reserved_activity.service, 'XMLRPC')

    def test_double_reserve(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        self.assert_(system.user is None)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('has already reserved system' in e.faultString)

class ReleaseSystemXmlRpcTest(XmlRpcTestCase):

    def test_cannot_release_when_not_logged_in(self):
        system = data_setup.create_system()
        session.flush()
        server = self.get_server()
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_(e.faultString.startswith(
                    'cherrypy._cperror.HTTPRedirect'))

    def test_cannot_release_when_not_current_user(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system.user = other_user
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is reserved by a different user'
                    in e.faultString)

    def test_release_system(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        system.user = user
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        session.refresh(system)
        self.assert_(system.user is None)
        released_activity = system.activity[-1]
        self.assertEqual(released_activity.action, 'Returned')
        self.assertEqual(released_activity.field_name, 'User')
        self.assertEqual(released_activity.user, user)
        self.assertEqual(released_activity.old_value, user.user_name)
        self.assertEqual(released_activity.new_value, '')
        self.assertEqual(released_activity.service, 'XMLRPC')

    def test_double_release(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        system.user = user
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is not reserved' in e.faultString)

class SystemPowerXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.stub_cobbler_thread.start()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        session.flush()
        self.server = self.get_server()

    def tearDown(self):
        self.stub_cobbler_thread.stop()

    def test_cannot_power_when_not_logged_in(self):
        try:
            self.server.systems.power('on', 'fqdn')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_(e.faultString.startswith(
                    'cherrypy._cperror.HTTPRedirect'))
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_cannot_power_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = other_user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.power('on', system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is in use' in e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def check_power_action(self, action):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system()
        data_setup.configure_system_power(system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        system.lab_controller = self.lab_controller
        system.user = None
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power(action, system.fqdn)
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.system_actions[system.fqdn],
                action)
        self.assertEqual(self.stub_cobbler_thread.cobbler.systems[system.fqdn],
                {'power_type': 'drac',
                 'power_address': 'nowhere.example.com',
                 'power_user': 'teh_powz0r',
                 'power_pass': 'onoffonoff',
                 'power_id': 'asdf'})

    def test_power_on(self):
        self.check_power_action('on')

    def test_power_off(self):
        self.check_power_action('off')

    def test_reboot(self):
        self.check_power_action('reboot')

    def test_can_force_powering_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system = data_setup.create_system()
        data_setup.configure_system_power(system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        system.lab_controller = self.lab_controller
        system.user = other_user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power('on', system.fqdn, False, True)
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.system_actions[system.fqdn],
                'on')

    def test_clear_netboot(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system()
        data_setup.configure_system_power(system)
        system.lab_controller = self.lab_controller
        system.user = None
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power('reboot', system.fqdn, True)
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.system_actions[system.fqdn],
                'reboot')
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.systems[system.fqdn]['netboot-enabled'],
                False)

class SystemProvisionXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.stub_cobbler_thread.start()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        self.distro = data_setup.create_distro()
        self.server = self.get_server()

    def tearDown(self):
        self.stub_cobbler_thread.stop()

    def test_cannot_provision_when_not_logged_in(self):
        try:
            self.server.systems.provision('fqdn', 'distro')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_(e.faultString.startswith(
                    'cherrypy._cperror.HTTPRedirect'))
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_cannot_provision_automated_system(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Automated', shared=True)
        user = data_setup.create_user(password=u'password')
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, 'distro')
        except xmlrpclib.Fault, e:
            # It's not really a permissions issue, but oh well
            self.assert_('has insufficient permissions to provision'
                    in e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_cannot_provision_system_in_use(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system.user = other_user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, 'distro')
        except xmlrpclib.Fault, e:
            self.assert_('Reserve a system before provisioning'
                    in e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_provision(self):
        kickstart = '''
            %%pre
            kickstart lol!
            do some stuff etc
            '''
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        data_setup.configure_system_power(system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        system.lab_controller = self.lab_controller
        user = data_setup.create_user(password=u'password')
        system.user = user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro.install_name,
                {'method': 'nfs'},
                'noapic',
                'noapic runlevel=3',
                kickstart)
        self.assertEqual(self.stub_cobbler_thread.cobbler.systems[system.fqdn],
                {'power_type': 'drac',
                 'power_address': 'nowhere.example.com',
                 'power_user': 'teh_powz0r',
                 'power_pass': 'onoffonoff',
                 'power_id': 'asdf',
                 'ksmeta': {'method': 'nfs'},
                 'kopts': 'noapic',
                 'kopts_post': 'noapic runlevel=3',
                 'profile': system.fqdn,
                 'netboot-enabled': True})
        kickstart_filename = '/var/lib/cobbler/kickstarts/%s.ks' % system.fqdn
        self.assertEqual(self.stub_cobbler_thread.cobbler.profiles[system.fqdn],
                {'kickstart': kickstart_filename,
                 'parent': self.distro.install_name})
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.kickstarts[kickstart_filename],
                'url --url=$tree\n#raw\n%s\n#end raw' % kickstart)
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.system_actions[system.fqdn],
                'reboot')

    def test_provision_without_reboot(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        data_setup.configure_system_power(system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        system.lab_controller = self.lab_controller
        user = data_setup.create_user(password=u'password')
        system.user = user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro.install_name,
                None, None, None, None,
                False) # this last one is reboot=False
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

class LegacyPushXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=658503
    def test_system_activity_shows_changes(self):
        system = data_setup.create_system()
        system.key_values_string.extend([
            Key_Value_String(Key.by_name(u'PCIID'), '1022:2000'),
            Key_Value_String(Key.by_name(u'PCIID'), '80ee:beef'),
        ])
        session.flush()
        self.server.legacypush(system.fqdn,
                {'PCIID': ['80ee:cafe', '80ee:beef']})
        session.refresh(system)
        self.assertEquals(system.activity[0].field_name, u'Key/Value')
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Added')
        self.assertEquals(system.activity[0].old_value, None)
        self.assertEquals(system.activity[0].new_value, u'PCIID/80ee:cafe')
        self.assertEquals(system.activity[1].field_name, u'Key/Value')
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Removed')
        self.assertEquals(system.activity[1].old_value, u'PCIID/1022:2000')
        self.assertEquals(system.activity[1].new_value, None)

    def test_bools_are_coerced_to_ints(self):
        system = data_setup.create_system()
        system.key_values_string.append(
                Key_Value_String(Key.by_name(u'HVM'), '0'))
        session.flush()

        self.server.legacypush(system.fqdn, {'HVM': False})
        session.refresh(system)
        self.assertEquals(len(system.activity), 0) # nothing has changed, yet

        self.server.legacypush(system.fqdn, {'HVM': True})
        session.refresh(system)
        self.assertEquals(system.activity[0].field_name, u'Key/Value')
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Added')
        self.assertEquals(system.activity[0].old_value, None)
        self.assertEquals(system.activity[0].new_value, u'HVM/1')

class PushXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=658503

    def test_system_activity_shows_changes_for_simple_attributes(self):
        system = data_setup.create_system()
        system.vendor = None
        system.model = None
        system.memory = None
        session.flush()
        self.server.push(system.fqdn,
                {'vendor': 'Acorn', 'model': 'Archimedes', 'memory': '16'})
        session.refresh(system)
        # no way to know in which order the changes will be recorded :-(
        changes = system.activity[:4]
        for change in changes:
            self.assertEquals(change.service, u'XMLRPC')
            self.assertEquals(change.action, u'Changed')
        changed_fields = set(change.field_name for change in changes)
        self.assertEquals(changed_fields,
                set(['checksum', 'vendor', 'model', 'memory']))

    def test_system_activity_shows_changes_for_arches(self):
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Arch': ['sparc32']})
        session.refresh(system)
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Added')
        self.assertEquals(system.activity[0].field_name, u'Arch')
        self.assertEquals(system.activity[0].old_value, None)
        self.assertEquals(system.activity[0].new_value, u'sparc32')
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Changed')
        self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_devices(self):
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Devices': [{
            'type': 'IDE', 'bus': u'pci', 'driver': u'PIIX_IDE',
            'vendorID': '8086', 'deviceID': '7111',
            'description': u'82371AB/EB/MB PIIX4 IDE',
            'subsysVendorID': '0000', 'subsysDeviceID': '0000',
        }]})
        session.refresh(system)
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Added')
        self.assertEquals(system.activity[0].field_name, u'Device')
        self.assertEquals(system.activity[0].old_value, None)
        # the new value will just be some random device id
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Changed')
        self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_cpu(self):
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Cpu': {
            'modelName': 'Intel(R) Core(TM) i7 CPU       M 620  @ 2.67GHz',
            'vendor': 'GenuineIntel', 'family': 6, 'stepping': 5, 'model': 37,
            'processors': 4, 'cores': 4, 'sockets': 1, 'speed': 2659.708,
            'CpuFlags': ['fpu', 'mmx', 'syscall', 'ssse3'],
        }})
        session.refresh(system)
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Changed')
        self.assertEquals(system.activity[0].field_name, u'CPU')
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Changed')
        self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_numa(self):
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Numa': {'nodes': 321}})
        session.refresh(system)
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Changed')
        self.assertEquals(system.activity[0].field_name, u'NUMA')
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Changed')
        self.assertEquals(system.activity[1].field_name, u'checksum')
