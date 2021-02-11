
# vim: set fileencoding=utf-8:

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import logging
import requests
from urlparse import urljoin
from urllib import urlencode, urlopen
import uuid
import lxml.etree
from turbogears.database import session
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction, \
        DatabaseTestCase
from bkr.inttest.assertions import assert_sorted
from bkr.server.model import Cpu, Key, Key_Value_String, System, \
    SystemStatus, SystemPermission, Job, Disk, User, Hypervisor
from bkr.inttest.server.webdriver_utils import check_system_search_results, login, \
    wait_for_animation
from bkr.inttest.server.requests_utils import patch_json, login as requests_login

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
        self.assertEquals(len(ths), 33)

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
        self.assert_(self.system_count(feed) >= 25, self.system_count(feed))
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
        self.assertEquals(self.system_count(feed), 
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
        self.assert_(self.feed_contains_system(feed, with_module.fqdn))
        self.assert_(not self.feed_contains_system(feed, without_module.fqdn))


class IpxeScriptHTTPTest(DatabaseTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller(fqdn='lab.ipxescript.httptest')

    def test_unknown_uuid(self):
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % uuid.uuid4())
        self.assertEquals(response.status_code, 404)

    def test_invalid_uuid(self):
        response = requests.get(get_server_base() +
                'systems/by-uuid/blerg/ipxe-script')
        self.assertEquals(response.status_code, 404)

    def test_recipe_not_provisioned_yet(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe, virt=True, lab_controller=self.lc)
            # VM is created but recipe.provision() hasn't been called yet
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        self.assertEquals(response.status_code, 503)

    def test_lab_incompatible_URLs(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(
                arch=u'x86_64', osmajor=u'Fedora20',
                lab_controllers=[self.lc],
                urls=[u'nfs://example.nfs.test:/path/to/os'])
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        self.assertEqual(response.status_code, 404)
        self.assertMultiLineEqual(
            response.text,
            'Lab lab.ipxescript.httptest does not provide HTTP or FTP URLs for distro tree: %s'
            % distro_tree.id)

    def test_recipe_provision_with_custom_distro(self):
        with session.begin():
            recipe = data_setup.create_recipe(custom_distro=True)
            self.assertIsNone(recipe.distro_tree)
            recipe.installation.tree_url = 'http://mydistro.dummylab.test/os/'
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        response.raise_for_status()
        self.assertMultiLineEqual(response.text, """#!ipxe
kernel http://mydistro.dummylab.test/os/pxeboot/vmlinuz console=tty0 console=ttyS0,115200n8 inst.ks=%s noverifyssl netboot_method=ipxe
initrd http://mydistro.dummylab.test/os/pxeboot/initrd
boot
""" % recipe.installation.rendered_kickstart.link)  # noqa: E501

    def test_recipe_provision_with_custom_distro_and_incompatible_url(self):
        with session.begin():
            recipe = data_setup.create_recipe(custom_distro=True)
            self.assertIsNone(recipe.distro_tree)
            recipe.installation.tree_url = 'nfs://mydistro.dummylab.test:/os/'
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        self.assertEqual(response.status_code, 404)
        self.assertMultiLineEqual(
            response.text,
            'Given tree URL nfs://mydistro.dummylab.test:/os/ incompatible with iPXE')

    def test_recipe_provisioned(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(
                    arch=u'x86_64', osmajor=u'Fedora20',
                    lab_controllers=[self.lc],
                    urls=[u'nfs://example.nfs.test:/path/to/os',
                          u'http://example.com/ipxe-test/F20/x86_64/os/'])
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, virt=True,
                    lab_controller=self.lc)
        response = requests.get(get_server_base() +
                'systems/by-uuid/%s/ipxe-script' % recipe.resource.instance_id)
        response.raise_for_status()
        self.assertEquals(response.text, """#!ipxe
kernel http://example.com/ipxe-test/F20/x86_64/os/pxeboot/vmlinuz console=tty0 console=ttyS0,115200n8 ks=%s ksdevice=bootif noverifyssl netboot_method=ipxe
initrd http://example.com/ipxe-test/F20/x86_64/os/pxeboot/initrd
boot
""" % recipe.installation.rendered_kickstart.link)  # noqa: E501

class SystemHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for systems: /systems/<fqdn>.

    Note that other system-related HTTP APIs are tested elsewhere 
    (e.g. /systems/<fqdn>/commands/ in test_system_commands.py).
    """
    maxDiff = None

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.lab_controller = data_setup.create_labcontroller()
            self.system = data_setup.create_system(owner=self.owner, shared=False,
                    lab_controller=self.lab_controller)
            self.policy = self.system.custom_access_policy
            self.policy.add_rule(everybody=True, permission=SystemPermission.reserve)
            self.privileged_group = data_setup.create_group()
            self.policy.add_rule(group=self.privileged_group,
                                 permission=SystemPermission.edit_system)

    def test_get_system(self):
        response = requests.get(get_server_base() + '/systems/%s/' % self.system.fqdn,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEquals(response.json()['fqdn'], self.system.fqdn)

    def test_get_system_with_running_hardware_scan_recipe(self):
        # The bug was a circular reference from system -> recipe -> system
        # which caused JSON serialization to fail.
        with session.begin():
            Job.inventory_system_job(data_setup.create_distro_tree(),
                    owner=self.owner, system=self.system)
            recipe = self.system.find_current_hardware_scan_recipe()
            data_setup.mark_recipe_running(recipe, system=self.system)
        response = requests.get(get_server_base() + '/systems/%s/' % self.system.fqdn,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        in_progress_scan = response.json()['in_progress_scan']
        self.assertEquals(in_progress_scan['recipe_id'], recipe.id)
        self.assertEquals(in_progress_scan['status'], u'Running')
        self.assertEquals(in_progress_scan['job_id'], recipe.recipeset.job.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1386074
    def test_get_system_returns_correct_id(self):
        # The bug was that Power.id was overwriting System.id.
        with session.begin():
            # The bug is not observable if the system and power rows both 
            # happen to have the same id, which is likely in the test suite 
            # since we always create system and power rows together. Create 
            # a throwaway system row without power, to ensure the autoincrement 
            # ids are not in sync.
            data_setup.create_system(with_power=False)
            system = data_setup.create_system(owner=self.owner)
            self.assertNotEqual(system.id, system.power.id)
            # The bug is only observable to users with access to view power settings.
            self.assertTrue(system.can_view_power(self.owner))
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        response = s.get(get_server_base() + '/systems/%s/' % system.fqdn,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['id'], system.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1386074
    def test_updating_power_returns_correct_id(self):
        # The bug was that Power.id was overwriting System.id
        with session.begin():
            system = data_setup.create_system(with_power=False, owner=self.owner)
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'power_type': 'ilo', 'power_address': 'nowhere'})
        response.raise_for_status()
        self.assertEqual(response.json()['id'], system.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206033
    def test_system_details_includes_disks(self):
        with session.begin():
            disk = Disk(model='Seagate Old', size=1024, sector_size=512, phys_sector_size=512)
            session.add(disk)
            self.system.disks.append(disk)

        expected = [{
            u'phys_sector_size': disk.phys_sector_size,
            u'sector_size': disk.sector_size,
            u'size': disk.size,
            u'model': disk.model,
        }]

        response = requests.get(
            get_server_base() + 'systems/%s' % self.system.fqdn)

        self.assertIn('disks', response.json())
        self.assertEqual(expected, response.json()['disks'])

    def test_set_active_policy_from_pool(self):
        with session.begin():
            user = data_setup.create_user()
            pool = data_setup.create_system_pool()
            pool.systems.append(self.system)
            pool.access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user)

        with session.begin():
            self.assertFalse(self.system.active_access_policy.grants
                             (user, SystemPermission.edit_system))

        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                'password': 'theowner'}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % self.system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
                         )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.active_access_policy.grants
                            (user, SystemPermission.edit_system))

        # attempt to set active policy to a pool policy when the system
        # is not in the pool
        with session.begin():
            pool = data_setup.create_system_pool()
            session.expire_all()
        response = patch_json(get_server_base() +
                              'systems/%s/' % self.system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
                        )
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text,
                          'To use a pool policy, the system must be in the pool first')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206034
    def test_system_details_includes_cpus(self):
        with session.begin():
            cpu = Cpu(cores=5,
                      family=6,
                      model=7,
                      model_name='Intel',
                      flags=['beer', 'frob'],
                      processors=6,
                      sockets=2,
                      speed=24,
                      stepping=2,
                      vendor='Transmeta')
            session.add(cpu)
            self.system.cpu = cpu

        response = requests.get(
            get_server_base() + 'systems/%s' % self.system.fqdn)
        json = response.json()
        self.assertEqual([u'beer', u'frob'], json['cpu_flags'])
        self.assertEqual(5, json['cpu_cores'])
        self.assertEqual(6, json['cpu_family'])
        self.assertEqual(7, json['cpu_model'])
        self.assertEqual(u'Intel', json['cpu_model_name'])
        self.assertEqual(True, json['cpu_hyper'])
        self.assertEqual(6, json['cpu_processors'])
        self.assertEqual(2, json['cpu_sockets'])
        self.assertEqual(24, json['cpu_speed'])
        self.assertEqual(2, json['cpu_stepping'])
        self.assertEqual('Transmeta', json['cpu_vendor'])

    def test_set_active_policy_to_custom_policy(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            self.system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user1)
            pool = data_setup.create_system_pool()
            pool.access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user2)
            self.system.active_access_policy = pool.access_policy

        self.assertFalse(self.system.active_access_policy.grants 
                        (user1, SystemPermission.edit_system))
        self.assertTrue(self.system.active_access_policy.grants
                         (user2, SystemPermission.edit_system))

        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                'password': 'theowner'}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % self.system.fqdn, session=s,
                              data={'active_access_policy': {'custom': True}},
                         )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.active_access_policy.grants \
                            (user1, SystemPermission.edit_system))

    # https://bugzilla.redhat.com/show_bug.cgi?id=980352
    def test_condition_report_length_is_enforced(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                'password': 'theowner'}).raise_for_status()
        response = patch_json(get_server_base() + 'systems/%s/' % self.system.fqdn,
                session=s, data={'status': 'Broken', 'status_reason': 'reallylong' * 500})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'System condition report is longer than 4000 characters')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_can_update_active_access_policy_with_edit_policy_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_policy, user=user)
            pool = data_setup.create_system_pool(systems=[system])
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': user.user_name,
                'password': 'password'}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(system.active_access_policy, pool.access_policy)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_cannot_update_active_access_policy_with_edit_system_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user)
            pool = data_setup.create_system_pool(systems=[system])
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': user.user_name,
                'password': 'password'}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
        )
        self.assertEquals(response.status_code, 403)
        self.assertIn('Cannot edit system access policy', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_cannot_update_system_details_with_edit_policy_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_policy, user=user)
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': user.user_name,
                'password': 'password'}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'fqdn': u'newfqdn'},
        )
        self.assertEquals(response.status_code, 403)
        self.assertIn('Cannot edit system', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_records_activity_on_changing_access_policy(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            pool.systems.append(system)
        # change the system active access policy to pool access policy
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': data_setup.ADMIN_USER,
                'password': data_setup.ADMIN_PASSWORD}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'pool_name': pool.name}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy, pool.access_policy)
            self.assertEquals(system.activity[-1].field_name, 'Active Access Policy')
            self.assertEquals(system.activity[-1].action, 'Changed')
            self.assertEquals(system.activity[-1].old_value, 'Custom access policy')
            self.assertEquals(system.activity[-1].new_value, 'Pool policy: %s' % unicode(pool))
        # change the system active access policy back to custom access policy
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': data_setup.ADMIN_USER,
                'password': data_setup.ADMIN_PASSWORD}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'custom': True}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy, system.custom_access_policy)
            self.assertEquals(system.activity[-2].field_name, 'Active Access Policy')
            self.assertEquals(system.activity[-2].action, 'Changed')
            self.assertEquals(system.activity[-2].old_value, 'Pool policy: %s' % unicode(pool))
            self.assertEquals(system.activity[-2].new_value, 'Custom access policy')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1290273
    def test_updating_access_policy_with_no_change_should_not_record_activity(self):
        with session.begin():
            system = data_setup.create_system()
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': data_setup.ADMIN_USER,
                'password': data_setup.ADMIN_PASSWORD}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'active_access_policy': {'custom': True}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy, system.custom_access_policy)
            self.assertEquals(system.activity, [])

    #  https://bugzilla.redhat.com/show_bug.cgi?id=1323885
    def test_update_lab_controller_with_lab_controller_object(self):
        with session.begin():
            system = data_setup.create_system()
            lc = data_setup.create_labcontroller()
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': data_setup.ADMIN_USER,
                'password': data_setup.ADMIN_PASSWORD}).raise_for_status()
        response = patch_json(get_server_base() +
                              'systems/%s/' % system.fqdn, session=s,
                              data={'lab_controller': {'fqdn': lc.fqdn}},
        )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(system.lab_controller, lc)
            self.assertEquals(system.activity[-1].field_name, 'Lab Controller')
            self.assertEquals(system.activity[-1].action, 'Changed')
            self.assertEquals(system.activity[-1].old_value, None)
            self.assertEquals(system.activity[-1].new_value, lc.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1387109
    def test_can_set_zero_quiescent_period(self):
        with session.begin():
            system = data_setup.create_system()
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': data_setup.ADMIN_USER,
                'password': data_setup.ADMIN_PASSWORD}).raise_for_status()
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'power_quiescent_period': 0})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(system.power.power_quiescent_period, 0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_give_to_deleted_user(self):
        with session.begin():
            system = data_setup.create_system()
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'owner': {'user_name': deleted_user.user_name}})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text,
                'Cannot change owner to deleted user %s' % deleted_user.user_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1591391
    def test_system_owner_username_is_truncated(self):
        with session.begin():
            system = data_setup.create_system()
            max_new_value_length = 60
            long_username = 'z' * max_new_value_length + 's'
            user_with_long_username = data_setup.create_user(user_name=long_username)
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'systems/%s/' % system.fqdn,
                session=s, data={'owner': {'user_name': user_with_long_username.user_name}})
        self.assertEquals(response.status_code, 200)
        with session.begin():
            self.assertEquals(system.activity[0].field_name, u'Owner')
            self.assertEquals(system.activity[0].action, u'Changed')
            self.assertEquals(system.activity[0].new_value, u'z' * max_new_value_length)
