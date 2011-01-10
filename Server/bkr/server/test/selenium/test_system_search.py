#!/usr/bin/python
from bkr.server.model import Numa
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

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
