
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from bkr.server.model import Numa, User, Key, Key_Value_String, Key_Value_Int, \
    Device, DeviceClass, Disk, Cpu, SystemPermission, System, \
    SystemType, SystemStatus, Hypervisor
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import get_server_base, login, \
        search_for_system, wait_for_animation, check_system_search_results
from bkr.inttest.assertions import assert_sorted
from bkr.inttest import data_setup, with_transaction, get_server_base
import unittest, time, re, os, datetime
from turbogears.database import session
from urlparse import urljoin

class SearchColumns(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_pool_column(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            system_in_pool = data_setup.create_system()
            system_in_pool.pools.append(pool)
            system_outside_pool = data_setup.create_system()
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Pools')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys(pool.name)
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select None').click()
        b.find_element_by_name('systemsearch_column_System/Name').click()
        b.find_element_by_name('systemsearch_column_System/Pools').click()
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[system_in_pool],
                                    absent=[system_outside_pool])
        b.find_element_by_xpath('//table[@id="widget"]'
                                '//td[2][normalize-space(text())="%s"]' % pool.name)

    def test_numa_column(self):
        with session.begin():
            system_with_numa = data_setup.create_system()
            system_with_numa.numa = Numa(nodes=2)
            system_without_numa = data_setup.create_system()
            system_without_numa.numa = None
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/NumaNodes')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is not')
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select None').click()
        b.find_element_by_name('systemsearch_column_System/Name').click()
        b.find_element_by_name('systemsearch_column_System/NumaNodes').click()
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[system_with_numa],
                absent=[system_without_numa])
        b.find_element_by_xpath('//table[@id="widget"]'
                '//td[2][normalize-space(text())="2"]')

    def test_serial_number_column(self):
        with session.begin():
            system_with_serial = data_setup.create_system()
            system_with_serial.serial = u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            system_without_serial = data_setup.create_system()
            system_without_serial.serial = None
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/SerialNumber')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        # This also tests that whitespace does not foil us
        b.find_element_by_name('systemsearch-0.value').send_keys(
                ' %s ' % system_with_serial.serial)
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select None').click()
        b.find_element_by_name('systemsearch_column_System/Name').click()
        b.find_element_by_name('systemsearch_column_System/SerialNumber').click()
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[system_with_serial],
                absent=[system_without_serial])
        b.find_element_by_xpath('//table[@id="widget"]'
                '//td[2][normalize-space(text())="%s"]' % system_with_serial.serial)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1010624
    def test_column_selection(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')

        b.find_element_by_link_text('Select None').click()
        b.find_element_by_link_text('Select Default').click()
        b.find_element_by_xpath("//form[@id='searchform']").submit()
        columns = b.find_elements_by_xpath("//table[@id='widget']//th")
        self.assertEquals(len(columns), 8)

        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select None').click()
        b.find_element_by_link_text('Select All').click()
        b.find_element_by_xpath("//form[@id='searchform']").submit()
        columns = b.find_elements_by_xpath("//table[@id='widget']//th")
        self.assertGreater(len(columns), 8)


def perform_search(browser, searchcriteria, search_url=''):
    b = browser
    b.get(get_server_base() + search_url)
    b.find_element_by_link_text('Show Search Options').click()
    wait_for_animation(b, '#searchform')

    for fieldid, criteria in enumerate(searchcriteria):
        if criteria[0] == 'Key/Value':
            assert len(criteria) == 4, "Key/Value criteria must be specified as" \
                    " ('Key/Value', keyname, operation, value)"
            fieldname, keyvalue, operation, value = criteria
        else:
            fieldname, operation, value = criteria
        if fieldid > 0:
            # press the add button to add a new row
            b.find_element_by_id('doclink').click()
        Select(b.find_element_by_name('systemsearch-%i.table' % fieldid))\
            .select_by_visible_text(fieldname)
        if criteria[0] == 'Key/Value':
            Select(browser.find_element_by_name('systemsearch-%i.keyvalue' % fieldid))\
                .select_by_visible_text(keyvalue)
        Select(b.find_element_by_name('systemsearch-%i.operation' % fieldid))\
            .select_by_visible_text(operation)
        b.find_element_by_name('systemsearch-%i.value' % fieldid).clear()
        b.find_element_by_name('systemsearch-%i.value' % fieldid).send_keys(value)

    b.find_element_by_id('searchform').submit()


class Search(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
            self.system = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller())
            self.system.loaned = self.user
            self.another_system = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller())
            self.another_system.loaned = self.user
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password=u'password')

    def test_multiple_cpu_flags(self):
        with session.begin():
            system = data_setup.create_system()
            system.cpu = Cpu(flags=['flag1', 'flag2'])
            another_system = data_setup.create_system()
            another_system.cpu = Cpu(flags=['flag3'])
        b = self.browser
        perform_search(b, [('CPU/Flags', 'is', 'flag1'),
                ('CPU/Flags', 'is', 'flag2')])
        check_system_search_results(b, present=[system],
                absent=[another_system])

    def test_by_device(self):
        with session.begin():
            system = data_setup.create_system()
            device = data_setup.create_device(
                    device_class='testclass',
                    subsys_vendor_id='1111',
                    subsys_device_id='1112')
            system.devices.append(device)
            another_system = data_setup.create_system()
            another_device = data_setup.create_device(
                    device_class='testclass',
                    subsys_vendor_id='2223',
                    subsys_device_id='2224')
            another_system.devices.append(another_device)
        b = self.browser
        perform_search(b, [('Devices/Subsys_device_id', 'is', '1112')])
        check_system_search_results(b, present=[system],
                absent=[another_system])

        perform_search(b, [('Devices/Subsys_vendor_id', 'is not', '1111'),
                             ('Devices/Subsys_device_id', 'is', '2224')])
        check_system_search_results(b, present=[another_system],
                absent=[system])

    def test_by_name(self):
        b = self.browser
        perform_search(b, [('System/Name', 'is', self.system.fqdn)])
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])

    def test_by_type(self):
        with session.begin():
            self.system.type = SystemType.laptop
        b = self.browser
        b.get(urljoin(get_server_base(),'mine'))
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Type')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text('Laptop')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])

    def test_by_status(self):
        with session.begin():
            self.system.status = SystemStatus.manual
        b = self.browser
        b.get(urljoin(get_server_base(),'mine'))
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Status')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text('Manual')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])

    def test_by_reserved_since(self):
        with session.begin():
            s1 = data_setup.create_system()
            data_setup.create_manual_reservation(s1, start=datetime.datetime(2003, 1, 21, 11, 30, 0))
            s2 = data_setup.create_system(fqdn='aaadvark.testdata')
            data_setup.create_manual_reservation(s2, start=datetime.datetime(2005, 1, 21, 11, 30, 0))
        b = self.browser

        perform_search(b, [('System/Reserved', 'is', '2003-01-21')])
        check_system_search_results(b, present=[s1], absent=[s2])

        perform_search(b, [('System/Reserved', 'before', '2005-1-21')])
        check_system_search_results(b, present=[s1], absent=[s2])

        perform_search(b, [('System/Reserved', 'after', '2005-1-21')])
        check_system_search_results(b, absent=[s1, s2])

        perform_search(b, [('System/Reserved', 'after', '2005-1-1')])
        check_system_search_results(b, present=[s2], absent=[s1])

    def test_by_date_added(self):
        with session.begin():
            new_system = data_setup.create_system()
            new_system.date_added = datetime.datetime(2025, 6, 21, 11, 30, 0)
            old_system = data_setup.create_system()
            old_system.date_added = datetime.datetime(2001, 1, 15, 14, 12, 0)

        b = self.browser
        perform_search(b, [('System/Added', 'is', '2001-01-15')])
        check_system_search_results(b, present=[old_system], absent=[new_system])

        perform_search(b, [('System/Added', 'before', '2001-01-16')])
        check_system_search_results(b, present=[old_system], absent=[new_system])

        perform_search(b, [('System/Added', 'after', '2025-12-31')])
        # no results
        b.find_element_by_xpath('//table[@id="widget" and not(.//td)]')

        perform_search(b, [('System/Added', 'after', '2025-06-20')])
        check_system_search_results(b, present=[new_system], absent=[old_system])

        perform_search(b, [('System/Added', 'after', '2025-06-20'),
                           ('System/Added', 'before', '2025-06-22')])
        check_system_search_results(b, present=[new_system], absent=[old_system])

    def test_by_notes(self):
        with session.begin():
            owner = data_setup.create_user()
            new_system = data_setup.create_system()
            new_system.add_note("Note1", owner)
            old_system = data_setup.create_system()
            old_system.add_note("Note2", owner)

        b = self.browser

        # System/Notes search is supposed to be case-insensitive
        perform_search(b, [('System/Notes', 'contains', 'nOTe1')])
        check_system_search_results(b, present=[new_system], absent=[old_system])

        # Specific search
        perform_search(b, [('System/Notes', 'is', 'Note2')])
        check_system_search_results(b, present=[old_system], absent=[new_system])

        # All systems without any note
        perform_search(b, [('System/Notes', 'is', '')])
        check_system_search_results(b, absent=[old_system, new_system])

        # All systems with any note
        perform_search(b, [('System/Notes', 'is not', '')])
        check_system_search_results(b, present=[old_system, new_system])

        perform_search(b, [('System/Notes', 'is', 'foobar')])
        # no results
        b.find_element_by_xpath('//table[@id="widget" and not(.//td)]')

    def test_by_key_value_is(self):
        with session.begin():
            self.system.key_values_string.append(Key_Value_String(
                    Key.by_name(u'CPUMODEL'), 'foocodename'))
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-0.keyvalue'))\
            .select_by_visible_text('CPUMODEL')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys('foocodename')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])

    def test_by_key_value_is_on_removed_systems_page(self):
        with session.begin():
            system = data_setup.create_system()
            removed_system = data_setup.create_system(status=SystemStatus.removed)
            removed_system.key_values_string.append(Key_Value_String(
                    Key.by_name(u'CPUMODEL'), 'foocodename'))
        # Key Value search from "Removed Systems"
        b = self.browser
        perform_search(b, [('Key/Value', 'CPUMODEL', 'is', 'foocodename')],
                search_url='removed')
        check_system_search_results(b, present=[removed_system],
                absent=[system])

    def test_by_key_value_is_not(self):
        with session.begin():
            self.another_system.key_values_string.append(Key_Value_String(
                    Key.by_name(u'CPUMODEL'), 'foocodename'))
        b = self.browser
        perform_search(b, [('Key/Value', 'CPUMODEL', 'is not', 'foocodename')],
                search_url=u'mine')
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])

    def test_by_multiple_key_values(self):
        with session.begin():
            self.system = data_setup.create_system()
            self.system.key_values_string.append(Key_Value_String(
                Key.by_name(u'CPUMODEL'), 'foocodename'))
            self.system.key_values_string.append(Key_Value_String(
                Key.by_name(u'HVM'), '1'))
            self.system.key_values_int.append(Key_Value_Int(
                Key.by_name(u'DISKSPACE'), '1024'))
        b = self.browser
        perform_search(b, [('Key/Value', 'HVM', 'is', '1'),
            ('Key/Value', 'CPUMODEL', 'is', 'foocodename'),
            ('Key/Value', 'DISKSPACE', 'greater than', '1000')])
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])


    def test_can_search_by_numa_node_count(self):
        with session.begin():
            self.system.numa = Numa(nodes=1)
            self.another_system.numa = Numa(nodes=2)
        b = self.browser
        perform_search(b, [('System/NumaNodes', 'greater than', '1')])
        check_system_search_results(b, present=[self.another_system],
                absent=[self.system])
        b.get(get_server_base())
        perform_search(b, [('System/NumaNodes', 'less than', '2')])
        check_system_search_results(b, present=[self.system],
                absent=[self.another_system])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1304927
    def test_search_works_on_reserve_report(self):
        # Reserve Report is a specialisation of the regular systems grid, so we 
        # aren't testing it exhaustively, we just want to make sure that the 
        # search is wired up properly.
        with session.begin():
            included = data_setup.create_system()
            data_setup.create_manual_reservation(included)
            excluded = data_setup.create_system(fqdn=data_setup.unique_name(u'aardvark%s'))
            data_setup.create_manual_reservation(excluded)
        b = self.browser
        perform_search(b, [('System/Name', 'is', included.fqdn)],
                search_url='reports/')
        check_system_search_results(b, present=[included], absent=[excluded])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1120705
    def test_searchbar_dropdowns_are_sorted(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        table_options = b.find_element_by_name('systemsearch-0.table')\
                .find_elements_by_tag_name('option')
        assert_sorted([option.text for option in table_options])
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Key/Value')
        keyvalue_options = b.find_element_by_name('systemsearch-0.keyvalue')\
                .find_elements_by_tag_name('option')
        assert_sorted([option.text for option in keyvalue_options])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1182545
    def test_invalid_date(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('after')
        search_field = b.find_element_by_name('systemsearch-0.value')
        search_field.click()
        # close the date picker
        search_field.send_keys(Keys.ESCAPE)
        search_field.send_keys('02-02-2002')
        # we can't actually check the HTML5 validation error
        b.find_element_by_css_selector('input[name="systemsearch-0.value"]:invalid')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1182545
    def test_date_picker(self):
        with session.begin():
            today = datetime.date.today()
            new_system = data_setup.create_system()
            new_system.date_added = today
            old_system = data_setup.create_system()
            old_system.date_added = today - datetime.timedelta(days=10)
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('before')
        search_field = b.find_element_by_name('systemsearch-0.value')
        search_field.click()
        b.find_element_by_css_selector('.datepicker td.active').click()
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[old_system], absent=[new_system])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215024
    def test_closing_script_tag_escaped_in_search_bar(self):
        with session.begin():
            Key.lazy_create(key_name=u'</script>')
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-0.keyvalue'))\
            .select_by_visible_text('</script>')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1295998
    def test_closing_script_tag_from_search_value_is_escaped(self):
        bad_string = u"</script><script>alert('hi')</script>"
        with session.begin():
            system = data_setup.create_system(location=bad_string)
            another_system = data_setup.create_system()
        b = self.browser
        perform_search(b, [('System/Location', 'is', bad_string)])
        check_system_search_results(b, present=[system],
                absent=[another_system])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1295998
    def test_closing_script_tag_from_simplesearch_is_escaped(self):
        bad_string = u"</script><script>alert('hi')</script>"
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_name('simplesearch').send_keys(bad_string)
        b.find_element_by_name('systemsearch_simple').submit()
        # System simplesearch matches on FQDN but we can never have an FQDN 
        # containing </script> so we can only expect empty results. The 
        # important thing is that there should not be a JS alert present.
        b.find_element_by_xpath('//span[@class="item-count" and text()="Items found: 0"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1498804
    def test_no_value(self):
        # This is just a bizarre edge case in how the existing search bar 
        # handles adding new rows to the search, causing the value control to 
        # be "unsuccessful" in HTML forms parlance.
        # Just delete this test when the search bar is improved in future.
        with session.begin():
            not_virtualised = data_setup.create_system(fqdn=u'bz1498804.notvirtualised')
            not_virtualised.hypervisor = None
            virtualised = data_setup.create_system(fqdn=u'bz1498804.virtualised')
            virtualised.hypervisor = Hypervisor.by_name(u'KVM')
        b = self.browser
        # Open a page with an existing search filled in.
        b.get(get_server_base() +
                '?systemsearch-0.table=System%2FName'
                '&systemsearch-0.operation=contains'
                '&systemsearch-0.value=bz1498804')
        # Add a new row to the search
        b.find_element_by_id('doclink').click()
        # Select a field, but don't type anything into the value
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('System/Hypervisor')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[not_virtualised], absent=[virtualised])

class LabControllerSearchTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password=u'password')
            self.lc1 = data_setup.create_labcontroller(fqdn=u'bz704399.example.invalid')
            self.lc2 = data_setup.create_labcontroller()

            self.s1 = data_setup.create_system(lab_controller=self.lc1, loaned=self.owner)
            self.s2 = data_setup.create_system(lab_controller=self.lc2, loaned=self.owner)

        self.browser = self.get_browser()
        login(self.browser, user=self.owner.user_name, password=u'password')

    def test_by_lab_controller(self):
        b = self.browser
        perform_search(b, [('System/LabController', 'is', self.lc1.fqdn)], search_url='mine')
        check_system_search_results(b, present=[self.s1], absent=[self.s2])

    def test_by_lab_controller_is_not(self):
        b = self.browser
        perform_search(b, [('System/LabController', 'is not', self.lc1.fqdn)], search_url='mine')
        check_system_search_results(b,
                                    present=[self.s2],
                                    absent=[self.s1])

    def test_by_lab_controller_contains(self):
        b = self.browser
        perform_search(b, [('System/LabController', 'contains', self.lc1.fqdn)], search_url='mine')
        check_system_search_results(b,
            present=[self.s1],
            absent=[self.s2])


class SystemVisibilityTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
        self.browser = self.get_browser()

    def test_secret_system_not_visible(self):
        with session.begin():
            secret_system = data_setup.create_system(shared=False, private=True)
        b = self.browser
        login(b, user=self.user.user_name, password=u'password')
        b.get(get_server_base())
        search_for_system(b, secret_system)
        # results grid should be empty
        b.find_element_by_xpath('//table[@id="widget" and not(.//td)]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=582008
    def test_secret_system_visible_when_loaned(self):
        with session.begin():
            secret_system = data_setup.create_system(shared=False, private=True)
            secret_system.loaned = self.user
        b = self.browser
        login(b, user=self.user.user_name, password=u'password')
        b.get(get_server_base())
        search_for_system(b, secret_system)
        b.find_element_by_xpath('//table[@id="widget"]'
                '//tr/td[1][./a/text()="%s"]' % secret_system.fqdn)

    def test_secret_system_visible_to_users_with_view_permission(self):
        with session.begin():
            secret_system = data_setup.create_system(shared=False, private=True)
            secret_system.custom_access_policy.add_rule(SystemPermission.view,
                    user=self.user)
        b = self.browser
        login(b, user=self.user.user_name, password=u'password')
        b.get(get_server_base())
        search_for_system(b, secret_system)
        b.find_element_by_xpath('//table[@id="widget"]'
                '//tr/td[1][./a/text()="%s"]' % secret_system.fqdn)

class HypervisorSearchTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'hypervisin')
            self.kvm = data_setup.create_system(loaned=self.user, hypervisor=u'KVM')
            self.xen = data_setup.create_system(loaned=self.user, hypervisor=u'Xen')
            self.phys = data_setup.create_system(loaned=self.user, hypervisor=None)
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password=u'hypervisin')

    def test_search_hypervisor_is(self):
        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Hypervisor')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text('KVM')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.kvm], absent=[self.xen, self.phys])

    def test_search_hypervisor_is_not(self):
        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Hypervisor')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is not')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text('KVM')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.xen, self.phys], absent=[self.kvm])

    def test_search_hypervisor_is_blank(self):
        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Hypervisor')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text('')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.phys], absent=[self.kvm, self.xen])


class DiskSearchTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'diskin')
            self.no_disks = data_setup.create_system(loaned=self.user)
            self.no_disks.disks[:] = []
            self.small_disk = data_setup.create_system(loaned=self.user)
            self.small_disk.disks[:] = [Disk(size=8000000000,
                    sector_size=512, phys_sector_size=512)]
            self.big_disk = data_setup.create_system(loaned=self.user)
            self.big_disk.disks[:] = [Disk(size=2000000000000,
                    sector_size=4096, phys_sector_size=4096)]
            self.two_disks = data_setup.create_system(loaned=self.user)
            self.two_disks.disks[:] = [
                Disk(size=8000000000, sector_size=512, phys_sector_size=512),
                Disk(size=2000000000000, sector_size=4096, phys_sector_size=4096),
            ]
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password=u'diskin')

    def test_search_size_greater_than(self):
        b = self.browser
        perform_search(b, [('Disk/Size', 'greater than', '10000000000')],
                search_url='mine')
        check_system_search_results(b, present=[self.big_disk, self.two_disks],
                absent=[self.small_disk, self.no_disks])

    def test_sector_size_is_not_for_multiple_disks(self):
        # The search bar special-cases "is not" searches on one-to-many 
        # relationships. "Disk/Size is not 1000" does not mean "systems with 
        # a disk whose size is not 1000" but rather "systems with no disks of 
        # size 1000".
        b = self.browser
        perform_search(b, [('Disk/SectorSize', 'is not', '512')],
                search_url='mine')
        check_system_search_results(b, present=[self.big_disk, self.no_disks],
                absent=[self.small_disk, self.two_disks])


#https://bugzilla.redhat.com/show_bug.cgi?id=949777
# we visit the 'mine' page, so that we have substantially
# less systems to deal with
class InventoriedSearchTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password=u'password')

    def test_uninventoried_search(self):
        with session.begin():
            system = data_setup.create_system(loaned=self.user)
        b = self.browser
        perform_search(b, [('System/LastInventoried', 'is', ' ')],
                search_url='mine')
        check_system_search_results(b, present=[system])

    def test_inventoried_search_after(self):
        with session.begin():
            system_one = data_setup.create_system(loaned=self.user)
            system_one.date_lastcheckin = datetime.datetime(2001, 1, 15, 14, 12, 0)
            system_two = data_setup.create_system(loaned=self.user)
            system_two.date_lastcheckin = datetime.datetime(2001, 1, 16, 14, 12, 0)
        b = self.browser
        perform_search(b, [('System/LastInventoried', 'after', '2001-01-15')],
                search_url='mine')
        check_system_search_results(b, present=[system_two], absent=[system_one])

    def test_inventoried_search_is(self):
        with session.begin():
            system = data_setup.create_system(loaned=self.user)
            system.date_lastcheckin = datetime.datetime(2001, 1, 15, 14, 12, 0)
        b = self.browser
        perform_search(b, [('System/LastInventoried', 'is', '2001-01-15')],
                search_url='mine')
        check_system_search_results(b, present=[system])

    def test_inventoried_search_before(self):
        with session.begin():
            system_one = data_setup.create_system(loaned=self.user)
            system_one.date_lastcheckin = datetime.datetime(2001, 1, 15, 14, 12, 0)
            system_two = data_setup.create_system(loaned=self.user)
            system_two.date_lastcheckin = datetime.datetime(2001, 1, 14, 14, 12, 0)
        b = self.browser
        perform_search(b, [('System/LastInventoried', 'before', '2001-01-15')],
                search_url='mine')
        check_system_search_results(b, present=[system_two], absent=[system_one])

    def test_inventoried_search_range(self):
        with session.begin():
            system_one = data_setup.create_system(loaned=self.user)
            system_one.date_lastcheckin = datetime.datetime(2001, 1, 15, 14, 12, 0)
            system_two = data_setup.create_system(loaned=self.user)
            system_two.date_lastcheckin = datetime.datetime(2001, 1, 14, 14, 12, 0)
            system_three = data_setup.create_system(loaned=self.user)
            system_three.date_lastcheckin = datetime.datetime(2001, 1, 16, 14, 12, 0)
        b = self.browser
        perform_search(b, [('System/LastInventoried', 'after', '2001-01-14'),
            ('System/LastInventoried', 'before', '2001-01-16')], search_url='mine')
        check_system_search_results(b, present=[system_one],
                absent=[system_two, system_three])
