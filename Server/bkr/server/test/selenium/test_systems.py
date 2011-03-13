
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
import logging
from urlparse import urljoin
from urllib import urlencode, urlopen
import lxml.etree
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup, get_server_base
from bkr.server.test.assertions import assert_sorted
from bkr.server.model import Cpu

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
                1)

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
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')

        cell_values = []
        while True:
            row_count = int(sel.get_xpath_count('//table[@id="widget"]/tbody/tr/td[%d]' % column))
            cell_values += [sel.get_table('widget.%d.%d' % (row, column - 1)) # zero-indexed 
                           for row in range(0, row_count)]
            # Keeping scrolling through pages until we have seen at least two distinct cell values
            # (so that we can see that it is really sorted)
            if len(set(cell_values)) > 1:
                break
            if sel.get_xpath_count('//div[@class="list"]//a[text()=">"]') != 1:
                raise AssertionError('Tried all pages, but every cell had the same value!')
            sel.click('//div[@class="list"]//a[text()=">"]')
            sel.wait_for_page_to_load('30000')
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
