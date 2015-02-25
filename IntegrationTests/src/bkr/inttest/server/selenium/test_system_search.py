
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from bkr.server.model import Numa, User, Key, Key_Value_String, Key_Value_Int, \
    Device, DeviceClass, Disk, Cpu, SystemPermission
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

    def test_group_column(self):
        with session.begin():
            group = data_setup.create_group()
            system_with_group = data_setup.create_system()
            system_with_group.groups.append(group)
            system_without_group = data_setup.create_system()
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Group')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys(group.group_name)
        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select None').click()
        b.find_element_by_name('systemsearch_column_System/Name').click()
        b.find_element_by_name('systemsearch_column_System/Group').click()
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[system_with_group],
                absent=[system_without_group])
        b.find_element_by_xpath('//table[@id="widget"]'
                '//td[2][normalize-space(text())="%s"]' % group.group_name)

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
        self.assertEquals(len(columns), 7)

        b.find_element_by_link_text('Toggle Result Columns').click()
        wait_for_animation(b, '#selectablecolumns')
        b.find_element_by_link_text('Select None').click()
        b.find_element_by_link_text('Select All').click()
        b.find_element_by_xpath("//form[@id='searchform']").submit()
        columns = b.find_elements_by_xpath("//table[@id='widget']//th")
        self.assertGreater(len(columns), 7)


class Search(WebDriverTestCase):

    @classmethod
    @with_transaction
    def setUpClass(cls):
        cls.system_one_details = { 'fqdn' : u'a1',
                                    'type' : u'Machine',
                                    'arch' : u'i386',
                                    'status' : u'Automated',
                                    'owner' : data_setup.create_user(),}
        cls.system_one = data_setup.create_system(**cls.system_one_details)
        cls.system_one.loaned = data_setup.create_user()
        cls.system_one.numa = Numa(nodes=2)
        cls.system_one.key_values_string.append(Key_Value_String(
            Key.by_name(u'CPUMODEL'), 'foocodename'))
        cls.system_one.key_values_string.append(Key_Value_String(
            Key.by_name(u'HVM'), '1'))
        cls.system_one.cpu = Cpu(flags=['flag1', 'flag2'])

        cls.system_one.key_values_int.append(Key_Value_Int(
            Key.by_name(u'DISKSPACE'), '1024'))
        cls.system_one.key_values_int.append(Key_Value_Int(
            Key.by_name(u'MEMORY'), '4096'))

        cls.system_two_details = { 'fqdn' : u'a2',
                                    'type' : u'Prototype',
                                    'arch' : u'x86_64',
                                    'status' : u'Manual',
                                    'owner' : data_setup.create_user(),}
        cls.system_two = data_setup.create_system(**cls.system_two_details)
        cls.system_two.key_values_int.append(Key_Value_Int(
            Key.by_name(u'DISKSPACE'), '900'))
        cls.system_two.key_values_string.append(Key_Value_String(
            Key.by_name(u'HVM'), '1'))

        device_class = DeviceClass.lazy_create(device_class='class_type')
        device1 = Device.lazy_create(vendor_id = '0000',
                                      device_id = '0000',
                                      subsys_vendor_id = '2223',
                                      subsys_device_id = '2224',
                                      bus = '0000',
                                      driver = '0000',
                                      device_class_id = device_class.id,
                                      description = 'blah')
        cls.system_two.devices.append(device1)
        cls.system_three_details = { 'fqdn' : u'a3',
                                    'type' : u'Laptop',
                                    'arch' : u'ia64',
                                    'status' : u'Automated',
                                    'owner' : data_setup.create_user(),}
        cls.system_three = data_setup.create_system(**cls.system_three_details)
        cls.system_three.numa = Numa(nodes=1)
        device2 = Device.lazy_create(vendor_id = '0000',
                                      device_id = '0000',
                                      subsys_vendor_id = '1111',
                                      subsys_device_id = '1112',
                                      bus = '0000',
                                      driver = '0000',
                                      device_class_id = device_class.id,
                                      description = 'blah')
        cls.system_three.devices.append(device2)

        cls.system_four_details = {'status' : u'Removed',}
        cls.system_four = data_setup.create_system(**cls.system_four_details)
        cls.system_four.key_values_string.append(Key_Value_String(
            Key.by_name(u'CPUMODEL'), 'foocodename'))

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def test_multiple_cpu_flags(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('CPU/Flags')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys('flag1')
        b.find_element_by_id('doclink').click()
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('CPU/Flags')
        Select(b.find_element_by_name('systemsearch-1.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-1.value').send_keys('flag2')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_one],
                absent=[self.system_two, self.system_three])

    def test_loaned_not_free(self):
        with session.begin():
            lc1 = data_setup.create_labcontroller()
            self.system_one.lab_controller=lc1

        b = self.browser
        b.get(get_server_base() + 'free')
        self.assertEquals(b.title, 'Free Systems')
        check_system_search_results(b, present=[], absent=[self.system_one])

        with session.begin():
            self.system_one.loaned = User.by_user_name(data_setup.ADMIN_USER)
        b.get(get_server_base() + 'free')
        self.assertEquals(b.title, 'Free Systems')
        check_system_search_results(b, present=[self.system_one])

    def test_by_device(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Devices/Subsys_device_id')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys('1112')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_three],
                absent=[self.system_one, self.system_two])

        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Devices/Subsys_vendor_id')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is not')
        b.find_element_by_name('systemsearch-0.value').send_keys('1111')
        b.find_element_by_id('doclink').click()
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('Devices/Subsys_device_id')
        Select(b.find_element_by_name('systemsearch-1.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-1.value').send_keys('2224')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_two],
                absent=[self.system_one, self.system_three])

    def test_by_name(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Name')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys(self.system_one.fqdn)
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_one],
                absent=[self.system_two, self.system_three])

    def test_by_type(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Type')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is not')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text(self.system_three_details['type'])
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_one, self.system_two],
                absent=[self.system_three])

    def test_by_status(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Status')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        Select(b.find_element_by_name('systemsearch-0.value'))\
            .select_by_visible_text(self.system_two_details['status'])
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_two],
                absent=[self.system_one, self.system_three])

    def test_by_date_added(self):
        with session.begin():
            new_system = data_setup.create_system()
            new_system.date_added = datetime.datetime(2020, 6, 21, 11, 30, 0)
            old_system = data_setup.create_system()
            old_system.date_added = datetime.datetime(2001, 1, 15, 14, 12, 0)

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys('2001-01-15')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[old_system], absent=[new_system])

        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('before')
        b.find_element_by_name('systemsearch-0.value').clear()
        b.find_element_by_name('systemsearch-0.value').send_keys('2001-01-16')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[old_system], absent=[new_system])

        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('after')
        b.find_element_by_name('systemsearch-0.value').clear()
        b.find_element_by_name('systemsearch-0.value').send_keys('2020-12-31')
        b.find_element_by_id('searchform').submit()
        # no results
        b.find_element_by_xpath('//table[@id="widget" and not(.//td)]')

        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('after')
        b.find_element_by_name('systemsearch-0.value').clear()
        b.find_element_by_name('systemsearch-0.value').send_keys('2020-06-20')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[new_system], absent=[old_system])

        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('after')
        b.find_element_by_name('systemsearch-0.value').clear()
        b.find_element_by_name('systemsearch-0.value').send_keys('2020-06-20')
        b.find_element_by_id('doclink').click()
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-1.operation'))\
            .select_by_visible_text('before')
        b.find_element_by_name('systemsearch-1.value').send_keys('2020-06-22')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[new_system], absent=[old_system])

    def test_by_key_value_is(self):
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
        check_system_search_results(b, present=[self.system_one],
                                    absent=[self.system_two, 
                                            self.system_three, 
                                            self.system_four])

        # Key Value search from "Removed Systems"
        b.get(urljoin(get_server_base(), 'removed'))
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
        check_system_search_results(b, present=[self.system_four],
                                    absent=[self.system_one, 
                                            self.system_two, 
                                            self.system_three])

    def test_by_key_value_is_not(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-0.keyvalue'))\
            .select_by_visible_text('CPUMODEL')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is not')
        b.find_element_by_name('systemsearch-0.value').send_keys('foocodename')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_two, self.system_three],
                absent=[self.system_one])

    def test_by_multiple_key_values(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-0.keyvalue'))\
            .select_by_visible_text('HVM')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys('1')
        b.find_element_by_id('doclink').click()
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-1.keyvalue'))\
            .select_by_visible_text('CPUMODEL')
        Select(b.find_element_by_name('systemsearch-1.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-1.value').send_keys('foocodename')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_one],
                absent=[self.system_two, self.system_three])

    def test_by_multiple_key_values_again(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-0.keyvalue'))\
            .select_by_visible_text('HVM')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
        b.find_element_by_name('systemsearch-0.value').send_keys('1')
        b.find_element_by_id('doclink').click()
        Select(b.find_element_by_name('systemsearch-1.table'))\
            .select_by_visible_text('Key/Value')
        Select(b.find_element_by_name('systemsearch-1.keyvalue'))\
            .select_by_visible_text('DISKSPACE')
        Select(b.find_element_by_name('systemsearch-1.operation'))\
            .select_by_visible_text('greater than')
        b.find_element_by_name('systemsearch-1.value').send_keys('1000')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_one],
                absent=[self.system_two, self.system_three])

    def test_can_search_by_numa_node_count(self):
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/NumaNodes')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('greater than')
        b.find_element_by_name('systemsearch-0.value').send_keys('1')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_one],
                absent=[self.system_two, self.system_three])

        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('less than')
        b.find_element_by_name('systemsearch-0.value').clear()
        b.find_element_by_name('systemsearch-0.value').send_keys('2')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.system_three],
                absent=[self.system_one, self.system_two])

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
        # test for using invalid date
        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('after')
        search_field = b.find_element_by_name('systemsearch-0.value')
        search_field.click()
        # close the date picker
        search_field.clear()
        search_field.send_keys(Keys.ESCAPE)
        search_field.clear()
        search_field.send_keys('02-02-2002')
        # we can't actually check the HTML5 validation error
        b.find_element_by_css_selector('input[name="systemsearch-0.value"]:invalid')

        Select(b.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Added')
        Select(b.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('before')
        search_field.click()
        date_picker = b.find_element_by_id('ui-datepicker-div')
        date_picker.find_element_by_class_name('ui-state-highlight').click()
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[old_system], absent=[new_system])


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
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('Disk/Size')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('greater than')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys('10000000000')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.big_disk, self.two_disks],
                absent=[self.small_disk, self.no_disks])

    def test_sector_size_is_not_for_multiple_disks(self):
        # The search bar special-cases "is not" searches on one-to-many 
        # relationships. "Disk/Size is not 1000" does not mean "systems with 
        # a disk whose size is not 1000" but rather "systems with no disks of 
        # size 1000".
        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('Disk/SectorSize')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('is not')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys('512')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.big_disk, self.no_disks],
                absent=[self.small_disk, self.two_disks])


#https://bugzilla.redhat.com/show_bug.cgi?id=949777
# we visit the 'mine' page, so that we have substantially
# less systems to deal with
class InventoriedSearchTest(WebDriverTestCase):

    @classmethod
    def setUpClass(cls):

        # date times
        cls.today = datetime.date.today()
        cls.time_now = datetime.datetime.combine(cls.today, datetime.time(0, 0))
        cls.time_delta1 = datetime.datetime.combine(cls.today, datetime.time(0, 30))
        cls.time_tomorrow = cls.time_now + datetime.timedelta(days=1)
        cls.time_yesterday = cls.time_now - datetime.timedelta(days=1)
        # today date
        cls.date_yesterday = cls.time_yesterday.date().isoformat()
        cls.date_today = cls.time_now.date().isoformat()
        cls.date_tomorrow = cls.time_tomorrow.date().isoformat()

        with session.begin():
            cls.user = data_setup.create_user(password=u'pass')
            cls.not_inv = data_setup.create_system(loaned=cls.user)

            cls.inv1 = data_setup.create_system(loaned=cls.user)
            cls.inv1.date_lastcheckin = cls.time_now

            cls.inv2 = data_setup.create_system(loaned=cls.user)
            cls.inv2.date_lastcheckin = cls.time_delta1

            cls.inv3 = data_setup.create_system(loaned=cls.user)
            cls.inv3.date_lastcheckin = cls.time_tomorrow

            cls.inv4 = data_setup.create_system(loaned=cls.user)
            cls.inv4.date_lastcheckin = cls.time_yesterday

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password='pass')

    def test_uninventoried_search(self):

        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('System/LastInventoried')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('is')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys(' ')
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.not_inv],
                absent=[self.inv1, self.inv2, self.inv3, self.inv4])

    def test_inventoried_search_after(self):

        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('System/LastInventoried')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('after')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys(self.date_today)
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.inv3],
                absent=[self.not_inv, self.inv1, self.inv2, self.inv4])

    def test_inventoried_search_is(self):

        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('System/LastInventoried')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('is')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys(self.date_today)
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.inv1, self.inv2],
                absent=[self.not_inv, self.inv3, self.inv4])

    def test_inventoried_search_before(self):

        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('System/LastInventoried')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('before')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys(self.date_today)
        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.inv4],
                absent=[self.not_inv, self.inv1, self.inv2, self.inv3])

    def test_inventoried_search_range(self):

        b = self.browser
        b.get(get_server_base() + 'mine')
        b.find_element_by_link_text('Show Search Options').click()
        wait_for_animation(b, '#searchform')

        #after
        Select(b.find_element_by_id('systemsearch_0_table'))\
            .select_by_visible_text('System/LastInventoried')
        Select(b.find_element_by_id('systemsearch_0_operation'))\
            .select_by_visible_text('after')
        b.find_element_by_id('systemsearch_0_value').clear()
        b.find_element_by_id('systemsearch_0_value').send_keys(self.date_yesterday)

        b.find_element_by_id('doclink').click()

        #before
        Select(b.find_element_by_id('systemsearch_1_table'))\
            .select_by_visible_text('System/LastInventoried')
        Select(b.find_element_by_id('systemsearch_1_operation'))\
            .select_by_visible_text('before')
        b.find_element_by_id('systemsearch_1_value').clear()
        b.find_element_by_id('systemsearch_1_value').send_keys(self.date_tomorrow)

        b.find_element_by_id('searchform').submit()
        check_system_search_results(b, present=[self.inv1, self.inv2],
                absent=[self.not_inv, self.inv3, self.inv4])
