#!/usr/bin/python
from bkr.server.model import Numa, User, Key, Key_Value_String, Key_Value_Int, \
    Device, DeviceClass
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import get_server_base, login, \
        search_for_system
from bkr.inttest import data_setup, with_transaction
import unittest, time, re, os, datetime
from turbogears.database import session

class SearchColumns(SeleniumTestCase):

    @classmethod
    @with_transaction
    def setUpClass(cls): 
        cls.group = data_setup.create_group()
        cls.system_with_group = data_setup.create_system(shared=True)
        cls.system_with_group.groups.append(cls.group)
        cls.system_with_numa = data_setup.create_system(shared=True)
        cls.system_with_numa.numa = Numa(nodes=2)
        cls.system_with_serial = data_setup.create_system()
        cls.system_with_serial.serial = u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    def test_group_column(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('30000')
        sel.click("advancedsearch")
        sel.select("systemsearch_0_table", "label=System/Group")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.click("customcolumns")
        sel.click("selectnone")
        sel.click("systemsearch_column_System/Group")
        sel.click("Search")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_with_group.groups[0].group_name))

    def test_numa_column(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('30000')
        sel.click("advancedsearch")
        sel.select("systemsearch_0_table", "label=System/NumaNodes")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.click("customcolumns")
        sel.click("selectnone")
        sel.click("systemsearch_column_System/NumaNodes")
        sel.click("Search")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present(str(self.system_with_numa.numa)))

    def test_serial_number_column(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('30000')
        sel.click('advancedsearch')
        sel.select('systemsearch_0_table', 'label=System/SerialNumber')
        sel.select('systemsearch_0_operation', 'label=is')
        sel.type('systemsearch_0_value', self.system_with_serial.serial)
        sel.click('customcolumns')
        sel.click('selectnone')
        sel.click('systemsearch_column_System/SerialNumber')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present(self.system_with_serial.serial))

    @classmethod
    def tearDownClass(cls):
        cls.selenium.stop()



class Search(SeleniumTestCase):

    @classmethod
    @with_transaction
    def setupClass(cls):
        cls.selenium = cls.get_selenium()
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
                                    'status' : u'Removed',
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
        cls.selenium.start()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.stop()

    def setUp(self):
        self.verificationErrors = []

    def test_loaned_not_free(self):
        sel = self.selenium
        self.login()
        sel.open('free')
        sel.wait_for_page_to_load("30000")
        self.assertEquals(sel.get_title(), 'Free Systems')
        self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))

        with session.begin():
            self.system_one.loaned = User.by_user_name(self.BEAKER_LOGIN_USER)
        sel.open('free')
        sel.wait_for_page_to_load("30000")
        self.assertEquals(sel.get_title(), 'Free Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))


    def test_system_search(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load("30000")
        sel.select("systemsearch_0_table", "label=Devices/Subsys_device_id")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "1112")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_two.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))


        sel.select("systemsearch_0_table", "label=Devices/Subsys_vendor_id")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.type("systemsearch_0_value", "1111")
        sel.click("doclink")

        sel.select("systemsearch_1_table", "label=Devices/Subsys_device_id")
        sel.select("systemsearch_1_operation", "label=is")
        sel.type("systemsearch_1_value", "2224")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_two.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))

        sel.open('')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_one.fqdn)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(1))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_two.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(2))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(3))

        sel.select("systemsearch_0_table", "label=System/Type")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.select("systemsearch_0_value", "label=%s" % self.system_three_details['type'])
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(4))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(5))
        
        sel.select("systemsearch_0_table", "label=System/Status")  
        sel.select("systemsearch_0_operation", "label=is")
        sel.select("systemsearch_0_value", "label=%s" % self.system_two_details['status'])
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(6))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(7))

        tomorrow_date = datetime.datetime.utcnow().date() + datetime.timedelta(days=1)
        tomorrow = tomorrow_date.isoformat()
        yesterday_date = datetime.datetime.utcnow().date() - datetime.timedelta(days=1)
        yesterday = yesterday_date.isoformat()
        sel.select("systemsearch_0_table", "label=System/Added")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % datetime.datetime.utcnow().date().isoformat())
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(8))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(9))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(10))

        sel.select("systemsearch_0_table", "label=System/Added")
        sel.select("systemsearch_0_operation", "label=before")
        sel.type("systemsearch_0_value", "%s" % tomorrow)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(11))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(12))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(13))

        sel.select("systemsearch_0_table", "label=System/Added")
        sel.select("systemsearch_0_operation", "label=after")
        sel.type("systemsearch_0_value", "%s" % tomorrow)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(14))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(15))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(16))

        sel.select("systemsearch_0_table", "label=System/Added")
        sel.select("systemsearch_0_operation", "label=after")
        sel.type("systemsearch_0_value", "%s" % yesterday)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(17))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(18))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(19))

        sel.select("systemsearch_0_table", "label=System/Added")
        sel.select("systemsearch_0_operation", "label=after")
        sel.type("systemsearch_0_value", "%s" % yesterday)
        sel.click("doclink")
        sel.select("systemsearch_1_table", "label=System/Added")
        sel.select("systemsearch_1_operation", "label=before")
        sel.type("systemsearch_1_value", "%s" % tomorrow)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(20))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(21))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(22))

    def test_can_search_by_key_value(self):
        sel = self.selenium
        sel.open('')
        sel.select("systemsearch_0_table", "label=Key/Value")
        sel.select("systemsearch_0_keyvalue", "label=CPUMODEL")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "foocodename")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        self.failUnless(sel.is_text_present("Items found: 1"))

        sel.open('')
        sel.select("systemsearch_0_table", "label=Key/Value")
        sel.select("systemsearch_0_keyvalue", "label=CPUMODEL")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.type("systemsearch_0_value", "foocodename")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))
        self.failUnless(sel.is_text_present("%s" % self.system_two.fqdn))
        self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))

        sel.open('')
        sel.select("systemsearch_0_table", "label=Key/Value")
        sel.select("systemsearch_0_keyvalue", "label=HVM")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "1")
        sel.click("doclink")
        sel.select("systemsearch_1_table", "label=Key/Value")
        sel.select("systemsearch_1_keyvalue", "label=CPUMODEL")
        sel.select("systemsearch_1_operation", "label=is")
        sel.type("systemsearch_1_value", "foocodename")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_two.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        self.failUnless(sel.is_text_present("Items found: 1"))

        # Search by Key_Value_Int and Key_Value_String and make
        # sure the right results are returned
        sel.open('')
        sel.select("systemsearch_0_table", "label=Key/Value")
        sel.select("systemsearch_0_keyvalue", "label=HVM")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "1")
        sel.click("doclink")
        sel.select("systemsearch_1_table", "label=Key/Value")
        sel.select("systemsearch_1_keyvalue", "label=DISKSPACE")
        sel.select("systemsearch_1_operation", "label=greater than")
        sel.type("systemsearch_1_value", "1000")
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_two.fqdn))
        self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        self.failUnless(sel.is_text_present("Items found: 1"))

        
        

    def test_can_search_by_numa_node_count(self):
        sel = self.selenium
        sel.open('')
        sel.select('systemsearch_0_table', 'label=System/NumaNodes')
        sel.select('systemsearch_0_operation', 'label=greater than')
        sel.type('systemsearch_0_value', '1')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        self.assert_(sel.is_text_present(self.system_one.fqdn))
        self.assert_(not sel.is_text_present(self.system_two.fqdn))
        self.assert_(not sel.is_text_present(self.system_three.fqdn))

        sel.select('systemsearch_0_table', 'label=System/NumaNodes')
        sel.select('systemsearch_0_operation', 'label=less than')
        sel.type('systemsearch_0_value', '2')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Systems')
        self.assert_(not sel.is_text_present(self.system_one.fqdn))
        self.assert_(not sel.is_text_present(self.system_two.fqdn))
        self.assert_(sel.is_text_present(self.system_three.fqdn))

    def tearDown(self):
        self.assertEqual([], self.verificationErrors)

class SearchWDTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_secret_system_not_visible(self):
        with session.begin():
            secret_system = data_setup.create_system()
            secret_system.private = True
        b = self.browser
        login(b, user=self.user.user_name, password=u'password')
        b.get(get_server_base())
        search_for_system(b, secret_system)
        # results grid should be empty
        b.find_element_by_xpath('//table[@id="widget" and not(.//td)]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=582008
    def test_secret_system_visible_when_loaned(self):
        with session.begin():
            secret_system = data_setup.create_system()
            secret_system.private = True
            secret_system.loaned = self.user
        b = self.browser
        login(b, user=self.user.user_name, password=u'password')
        b.get(get_server_base())
        search_for_system(b, secret_system)
        b.find_element_by_xpath('//table[@id="widget"]'
                '//tr/td[1][./a/text()="%s"]' % secret_system.fqdn)

class HypervisorSearchTest(SeleniumTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'hypervisin')
            self.kvm = data_setup.create_system(loaned=self.user, hypervisor=u'KVM')
            self.xen = data_setup.create_system(loaned=self.user, hypervisor=u'Xen')
            self.phys = data_setup.create_system(loaned=self.user, hypervisor=None)
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login(user=self.user.user_name, password=u'hypervisin')

    def tearDown(self):
        self.selenium.stop()

    def test_search_hypervisor_is(self):
        sel = self.selenium
        sel.open('mine')
        sel.select('systemsearch_0_table', 'label=System/Hypervisor')
        self.wait_for_condition(lambda: sel.is_element_present('//select[@id="systemsearch_0_value"]'))
        sel.select('systemsearch_0_operation', 'label=is')
        sel.select('systemsearch_0_value', 'KVM')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'My Systems')
        row_count = int(sel.get_xpath_count('//table[@id="widget"]/tbody/tr'))
        self.assertEquals(row_count, 1)
        self.assertEquals(sel.get_text('//table[@id="widget"]/tbody/tr[1]/td[1]'),
                self.kvm.fqdn)

    def test_search_hypervisor_is_not(self):
        sel = self.selenium
        sel.open('mine')
        sel.select('systemsearch_0_table', 'label=System/Hypervisor')
        self.wait_for_condition(lambda: sel.is_element_present('//select[@id="systemsearch_0_value"]'))
        sel.select('systemsearch_0_operation', 'label=is not')
        sel.select('systemsearch_0_value', 'KVM')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'My Systems')
        row_count = int(sel.get_xpath_count('//table[@id="widget"]/tbody/tr'))
        self.assertEquals(row_count, 2)
        self.assertEquals(sel.get_text('//table[@id="widget"]/tbody/tr[1]/td[1]'),
                self.xen.fqdn)
        self.assertEquals(sel.get_text('//table[@id="widget"]/tbody/tr[2]/td[1]'),
                self.phys.fqdn)

    def test_search_hypervisor_is_blank(self):
        sel = self.selenium
        sel.open('mine')
        sel.select('systemsearch_0_table', 'label=System/Hypervisor')
        self.wait_for_condition(lambda: sel.is_element_present('//select[@id="systemsearch_0_value"]'))
        sel.select('systemsearch_0_operation', 'label=is')
        sel.select('systemsearch_0_value', '')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'My Systems')
        row_count = int(sel.get_xpath_count('//table[@id="widget"]/tbody/tr'))
        self.assertEquals(row_count, 1)
        self.assertEquals(sel.get_text('//table[@id="widget"]/tbody/tr[1]/td[1]'),
                self.phys.fqdn)
