
# vim: set fileencoding=utf-8:

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from urlparse import urljoin
from urllib import urlencode, urlopen
import lxml.etree
from bkr.server.database import session
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction, \
        DatabaseTestCase
from bkr.inttest.assertions import assert_sorted
from bkr.server.model import Cpu, Key, Key_Value_String, System, \
    SystemStatus, User, Hypervisor
from bkr.inttest.server.webdriver_utils import wait_for_animation

def atom_xpath(expr):
    return lxml.etree.XPath(expr, namespaces={'atom': 'http://www.w3.org/2005/Atom'})

class TestSystemsGrid(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        data_setup.create_system()
        self.browser = self.get_browser()

    def test_atom_feed_link_is_present(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_xpath('/html/head/link[@rel="feed" '
                'and @title="Atom feed" and contains(@href, "tg_format=atom")]')

    def show_all_columns(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Name')
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select All').click()
        # Wait for checkboxes to be checked
        b.find_element_by_css_selector('#selectablecolumns input:checked')
        b.find_element_by_id('searchform').submit()
        # Wait for the new page to load (the row header changes from Name to
        # System-Name when all columns are shown)
        b.find_element_by_xpath('//table[@id="widget"]/thead/tr/th/a[text()="System-Name"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=704082
    def test_show_all_columns_works(self):
        self.show_all_columns()

        b = self.browser
        # check number of columns in the table
        ths = b.find_elements_by_xpath('//table[@id="widget"]//th')
        self.assertEqual(len(ths), 33)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1321740
    def test_grid_columns_order_is_preserved(self):
        self.show_all_columns()

        b = self.browser
        # headings should stay sorted after a reload
        headings = [th.text for th in
                b.find_elements_by_xpath('//table[@id="widget"]/thead//th')]
        header_link = b.find_element_by_link_text('System-Name')
        header_link.click()
        # Nothing changes on the page when sorting, so we have to use this 
        # trick to detect when the new page is loaded. This doesn't apply to 
        # Backgrids (they have sort indicators).
        WebDriverWait(b, 10).until(staleness_of(header_link))

        new_headings = [th.text for th in
                        b.find_elements_by_xpath('//table[@id="widget"]/thead//th')]
        self.assertEqual(headings, new_headings)

    def test_first_columns_order_is_fixed(self):
        expected_headings = ['System-Name', 'System-Arch', 'System-Vendor', 'System-Model']
        self.show_all_columns()

        b = self.browser
        headings = [th.text for th in
                b.find_elements_by_xpath('//table[@id="widget"]/thead//th')]

        # these headings should always be the first in that order
        self.assertEqual(expected_headings, headings[:4])

        # they stay fixed even after a reload
        header_link = b.find_element_by_link_text('System-Name')
        header_link.click()
        # Nothing changes on the page when sorting, so we have to use this 
        # trick to detect when the new page is loaded. This doesn't apply to 
        # Backgrids (they have sort indicators).
        WebDriverWait(b, 10).until(staleness_of(header_link))
        headings = [th.text for th in
                b.find_elements_by_xpath('//table[@id="widget"]/thead//th')]
        self.assertEqual(expected_headings, headings[:4])


class TestSystemsGridSorting(WebDriverTestCase):

    @classmethod
    def setUpClass(cls):
        with session.begin():
            # ensure we have lots of systems
            for cores in [1, 2, 3]:
                for vendor, model, status, type, reserved_since, user in zip(
                        [u'Acer', u'Dell', u'HP'],
                        [u'slow model', u'fast model', u'big model'],
                        [u'Automated', u'Manual', u'Removed'],
                        [u'Machine', u'Prototype'],
                        [datetime.datetime(2012, 10, 31, 23, 0, 0),
                         datetime.datetime(2015, 1, 1, 6, 0, 0),
                         datetime.datetime(2020, 1, 6, 10, 0, 0),
                        ],
                        [data_setup.create_user() for _ in range(3)]):
                    system = data_setup.create_system(vendor=vendor,
                            model=model, status=status, type=type)
                    system.cpu = Cpu(cores=cores)
                    system.user = user
                    system.lab_controller = data_setup.create_labcontroller()
                    data_setup.create_manual_reservation(system,
                                                         reserved_since,
                                                         user=user)

    def setUp(self):
        self.browser = self.get_browser()

    # https://bugzilla.redhat.com/show_bug.cgi?id=651418

    def check_column_sort(self, column_heading):
        b = self.browser
        column_headings = [th.text for th in
                b.find_elements_by_xpath('//table[@id="widget"]/thead//th')]
        self.assertIn(column_heading, column_headings)
        column_index = column_headings.index(column_heading) + 1 # xpath indices are 1-based
        b.find_element_by_xpath('//table[@id="widget"]/thead//th[%d]//a' % column_index).click()

        cell_values = []
        # Next page number
        # Assume our current page is 1
        next_page = 2
        while True:
            cell_values.extend(cell.text for cell in
                    b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr/td[%d]' % column_index))
            # Keeping scrolling through pages until we have seen at least two distinct cell values
            # (so that we can see that it is really sorted)
            if len(set(cell_values)) > 1:
                break
            try:
                b.find_element_by_xpath('//div[contains(@class, "pagination")]'
                        '//ul/li/a[normalize-space(string())="%s"]' % next_page).click()
            except NoSuchElementException:
                raise AssertionError('Tried all pages, but every cell had the same value!')
            next_page += 1
        assert_sorted(cell_values, key=lambda x: x.lower())

    # We test both ordinary listing (i.e. with no search query) as well as 
    # searching, because they go through substantially different code paths

    def go_to_listing(self):
        self.browser.get(get_server_base())

    def go_to_search_results(self, display_columns=None):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('CPU/Cores')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('greater than')
        b.find_element_by_name('systemsearch-0.value').send_keys('1')
        b.find_element_by_link_text('Add').click()
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('System/Name')
        Select(b.find_element_by_name('systemsearch-1.operation'))\
            .select_by_visible_text('is not')
        b.find_element_by_name('systemsearch-1.value').send_keys('bob')

        if display_columns is None:
            display_columns = []
        for column in display_columns:
            b.find_element_by_link_text('Toggle Result Columns').click()
            wait_for_animation(b, '#selectablecolumns')
            checkbox = b.find_element_by_id('systemsearch_column_%s' % column)
            if not checkbox.is_selected():
                checkbox.click()

        b.find_element_by_id('searchform').submit()
        b.find_element_by_xpath('//title[text()="Systems"]')

    def test_can_sort_listing_by_status(self):
        self.go_to_listing()
        self.check_column_sort('Status')

    def test_can_sort_listing_by_vendor(self):
        self.go_to_listing()
        self.check_column_sort('Vendor')

    def test_can_sort_listing_by_model(self):
        self.go_to_listing()
        self.check_column_sort('Model')

    def test_can_sort_listing_by_user(self):
        self.go_to_listing()
        self.check_column_sort('User')

    def test_can_sort_listing_by_type(self):
        self.go_to_listing()
        self.check_column_sort('Type')

    def test_can_sort_search_results_by_vendor(self):
        self.go_to_search_results()
        self.check_column_sort('Vendor')

    def test_can_sort_search_results_by_user(self):
        self.go_to_search_results()
        self.check_column_sort('User')

    def test_can_sort_search_results_by_type(self):
        self.go_to_search_results()
        self.check_column_sort('Type')

    def test_can_sort_search_results_by_status(self):
        self.go_to_search_results()
        self.check_column_sort('Status')

    def test_can_sort_search_results_by_model(self):
        self.go_to_search_results()
        self.check_column_sort('Model')

    def test_can_sort_search_results_by_reserved(self):
        self.go_to_search_results()
        b = self.browser
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_name('systemsearch_column_System/Reserved').click()
        b.find_element_by_id('searchform').submit()
        self.check_column_sort('Reserved')

    def test_can_sort_search_results_by_lab_controller(self):
        self.go_to_search_results(['System/LabController'])
        self.check_column_sort('LabController')


class TestSystemsAtomFeed(DatabaseTestCase):

    def feed_contains_system(self, feed, fqdn):
        xpath = atom_xpath('/atom:feed/atom:entry/atom:title[text()="%s"]' % fqdn)
        return len(xpath(feed))

    def system_count(self, feed):
        xpath = atom_xpath('count(/atom:feed/atom:entry)')
        return int(xpath(feed))

    def test_all_systems(self):
        with session.begin():
            systems = [data_setup.create_system() for _ in range(25)]
            removed_system = data_setup.create_system(status=SystemStatus.removed)

        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assertTrue(self.system_count(feed) >= 25, self.system_count(feed))
        for system in systems:
            self.assertTrue(self.feed_contains_system(feed, system.fqdn))
        self.assertFalse(self.feed_contains_system(feed, removed_system.fqdn))

    def test_removed_systems(self):
        with session.begin():
            system1 = data_setup.create_system(status=SystemStatus.removed)
            system2 = data_setup.create_system()

        feed_url = urljoin(get_server_base(), 'removed?' + urlencode({
            'tg_format': 'atom', 'list_tgp_order': '-date_modified',
            'list_tgp_limit': '0'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assertEqual(self.system_count(feed), 
                          System.query.filter(System.status==SystemStatus.removed).count())
        self.assertTrue(self.feed_contains_system(feed, system1.fqdn))
        self.assertFalse(self.feed_contains_system(feed, system2.fqdn))

    def test_link_to_rdfxml(self):
        with session.begin():
            system = data_setup.create_system()
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
        with session.begin():
            system = data_setup.create_system()
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

    def test_filter_by_pool(self):
        with session.begin():
            data_setup.create_system(fqdn=u'nopool.system')
            pool = data_setup.create_system_pool()
            data_setup.create_system(fqdn=u'inpool.system').pools.append(pool)
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'systemsearch-0.table': 'System/Pools',
                'systemsearch-0.operation': 'is',
                'systemsearch-0.value': pool.name}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assertFalse(self.feed_contains_system(feed, 'nopool.system'))
        self.assertTrue(self.feed_contains_system(feed, 'inpool.system'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1217158
    def test_filter_by_group(self):
        # System groups became pools in Beaker 20.0 but we need to continue 
        # supporting System/Group search (mapped to pools) for old clients.
        with session.begin():
            pool = data_setup.create_system_pool()
            nopool = data_setup.create_system()
            inpool = data_setup.create_system()
            inpool.pools.append(pool)
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom',
                'systemsearch-0.table': 'System/Group',
                'systemsearch-0.operation': 'is',
                'systemsearch-0.value': pool.name}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assertFalse(self.feed_contains_system(feed, nopool.fqdn))
        self.assertTrue(self.feed_contains_system(feed, inpool.fqdn))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1498804
    def test_filter_with_no_value(self):
        with session.begin():
            not_virtualised = data_setup.create_system()
            not_virtualised.hypervisor = None
            virtualised = data_setup.create_system()
            virtualised.hypervisor = Hypervisor.by_name(u'KVM')
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom',
                'list_tgp_order': '-date_modified',
                'list_tgp_limit': '0',
                'systemsearch-0.table': 'System/Hypervisor',
                'systemsearch-0.operation': 'is'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assertFalse(self.feed_contains_system(feed, virtualised.fqdn))
        self.assertTrue(self.feed_contains_system(feed, not_virtualised.fqdn))

    # https://bugzilla.redhat.com/show_bug.cgi?id=690063
    def test_xml_filter(self):
        with session.begin():
            module_key = Key.by_name(u'MODULE')
            with_module = data_setup.create_system()
            with_module.key_values_string.extend([
                    Key_Value_String(module_key, u'cciss'),
                    Key_Value_String(module_key, u'kvm')])
            without_module = data_setup.create_system()
        feed_url = urljoin(get_server_base(), '?' + urlencode({
                'tg_format': 'atom', 'list_tgp_order': '-date_modified',
                'xmlsearch': '<key_value key="MODULE" />'}))
        feed = lxml.etree.parse(urlopen(feed_url)).getroot()
        self.assertTrue(self.feed_contains_system(feed, with_module.fqdn))
        self.assertTrue(not self.feed_contains_system(feed, without_module.fqdn))

