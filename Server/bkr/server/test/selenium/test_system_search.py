#!/usr/bin/python
from bkr.server.model import Numa, User
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os, datetime
from turbogears.database import session

class SearchColumns(bkr.server.test.selenium.SeleniumTestCase):

    @classmethod
    def setUpClass(cls): 
        cls.group = data_setup.create_group()
        cls.system_with_group = data_setup.create_system(shared=True)
        cls.system_with_group.groups.append(cls.group)
        cls.system_with_numa = data_setup.create_system(shared=True)
        cls.system_with_numa.numa = Numa(nodes=2)
        cls.system_with_serial = data_setup.create_system()
        cls.system_with_serial.serial = u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        session.flush()
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    def test_group_column(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('3000')
        sel.click("advancedsearch")
        sel.select("systemsearch_0_table", "label=System/Group")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.click("customcolumns")
        sel.click("selectnone")
        sel.click("systemsearch_column_System/Group")
        sel.click("Search")
        sel.wait_for_page_to_load("3000")
        self.assertEqual(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_with_group.groups[0].group_name))

    def test_numa_column(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load('3000')
        sel.click("advancedsearch")
        sel.select("systemsearch_0_table", "label=System/NumaNodes")
        sel.select("systemsearch_0_operation", "label=is not")
        sel.click("customcolumns")
        sel.click("selectnone")
        sel.click("systemsearch_column_System/NumaNodes")
        sel.click("Search")
        sel.wait_for_page_to_load("3000")
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



class Search(bkr.server.test.selenium.SeleniumTestCase):

    @classmethod
    def setUpClass(cls):
        cls.selenium = cls.get_selenium()
        cls.system_one_details = { 'fqdn' : u'a1',
                                    'type' : u'Machine',
                                    'arch' : u'i386',
                                    'status' : u'Automated',
                                    'owner' : data_setup.create_user(),}
        cls.system_one = data_setup.create_system(**cls.system_one_details)
        cls.system_one.loaned = data_setup.create_user()
        cls.system_one.numa = Numa(nodes=2)

        cls.system_two_details = { 'fqdn' : u'a2',
                                    'type' : u'Virtual',
                                    'arch' : u'x86_64',
                                    'status' : u'Manual',
                                    'owner' : data_setup.create_user(),}
        cls.system_two = data_setup.create_system(**cls.system_two_details)

        cls.system_three_details = { 'fqdn' : u'a3',
                                    'type' : u'Laptop',
                                    'arch' : u'ia64',
                                    'status' : u'Removed',
                                    'owner' : data_setup.create_user(),}
        cls.system_three = data_setup.create_system(**cls.system_three_details)
        cls.system_three.numa = Numa(nodes=1)
        session.flush()
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
        self.assertEquals(sel.get_title(), 'Systems')
        self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))

        self.system_one.loaned = User.by_user_name(self.BEAKER_LOGIN_USER)
        session.flush()
        sel.open('free')
        sel.wait_for_page_to_load("30000")
        self.assertEquals(sel.get_title(), 'Systems')
        self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))


    def test_system_search(self):
        sel = self.selenium
        sel.open('')
        sel.wait_for_page_to_load("30000")
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_one.fqdn)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
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
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(4))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(5))
        
        sel.select("systemsearch_0_table", "label=System/Status")  
        sel.select("systemsearch_0_operation", "label=is")
        sel.select("systemsearch_0_value", "label=%s" % self.system_two_details['status'])
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(6))
        try: self.failUnless(not sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(7))

        tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
        tomorrow = tomorrow_date.isoformat()
        yesterday_date = datetime.date.today() - datetime.timedelta(days=1)
        yesterday = yesterday_date.isoformat()
        sel.select("systemsearch_0_table", "label=System/Added")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % datetime.datetime.utcnow().date().isoformat())
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
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
        self.assertTrue('Systems' in sel.get_title())
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
        try: self.failUnless(sel.is_text_present("%s" % self.system_one.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(20))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(21))
        try: self.failUnless(sel.is_text_present("%s" % self.system_three.fqdn))
        except AssertionError, e: self.verificationErrors.append(str(22))

    def test_can_search_by_numa_node_count(self):
        sel = self.selenium
        sel.open('')
        sel.select('systemsearch_0_table', 'label=System/NumaNodes')
        sel.select('systemsearch_0_operation', 'label=greater than')
        sel.type('systemsearch_0_value', '1')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assert_(sel.is_text_present(self.system_one.fqdn))
        self.assert_(not sel.is_text_present(self.system_two.fqdn))
        self.assert_(not sel.is_text_present(self.system_three.fqdn))

        sel.select('systemsearch_0_table', 'label=System/NumaNodes')
        sel.select('systemsearch_0_operation', 'label=less than')
        sel.type('systemsearch_0_value', '2')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assert_(not sel.is_text_present(self.system_one.fqdn))
        self.assert_(not sel.is_text_present(self.system_two.fqdn))
        self.assert_(sel.is_text_present(self.system_three.fqdn))

    def tearDown(self):
        self.assertEqual([], self.verificationErrors)
