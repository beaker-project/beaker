from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import Group
import unittest, time, re, os
from turbogears.database import session

class SystemAvailable(SeleniumTestCase):
 
    @with_transaction
    def setUp(self):
        self.selenium = self.get_selenium()
        self.password = 'password'

        # create users
        self.user_1 = data_setup.create_user(password=self.password)
        self.user_2 = data_setup.create_user(password=self.password)
        self.user_3 = data_setup.create_user(password=self.password)

        # create admin users
        self.admin_1 = data_setup.create_user(password=self.password)
        self.admin_1.groups.append(Group.by_name(u'admin'))
        self.admin_2 = data_setup.create_user(password=self.password)
        self.admin_2.groups.append(Group.by_name(u'admin'))

        # create systems
        self.system_1 = data_setup.create_system(shared=True)
        self.system_2 = data_setup.create_system(shared=True)
        self.system_3 = data_setup.create_system(shared=False,
                                                 owner=self.user_3)

        # create group and add users/systems to it
        self.group_1 = data_setup.create_group()
        self.user_3.groups.append(self.group_1)
        self.admin_2.groups.append(self.group_1)
        self.system_2.groups.append(self.group_1)

        lc = data_setup.create_labcontroller()
        self.system_1.lab_controller = lc
        self.system_2.lab_controller = lc
        self.system_3.lab_controller = lc

        self.selenium.start()

    def test_avilable_with_no_loan(self):
        self.login(user=self.user_1,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_1.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(sel.is_text_present(self.system_1.fqdn))
        sel.open("view/%s" % self.system_1.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))
        self.logout()

    def test_free_with_no_loan(self):
        self.login(user=self.user_1,password=self.password)
        sel = self.selenium
        sel.open('free/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_1.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Free Systems')
        self.failUnless(sel.is_text_present(self.system_1.fqdn))
        sel.open("view/%s" % self.system_1.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))
        self.logout()

    def test_avilable_with_loan(self):
        with session.begin():
            self.system_1.loaned=self.user_2
        self.login(user=self.user_1,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_1.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(sel.is_text_present(self.system_1.fqdn))
        sel.open("view/%s" % self.system_1.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))

    def test_free_with_loan(self):
        with session.begin():
            self.system_1.loaned=self.user_2
        self.login(user=self.user_1,password=self.password)
        sel = self.selenium
        sel.open('free/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_1.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Free Systems')
        self.failUnless(not sel.is_text_present(self.system_1.fqdn))
        sel.open("view/%s" % self.system_1.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))

    def test_not_available_system_2(self):
        self.login(user=self.user_1,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_2.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(not sel.is_text_present(self.system_2.fqdn))
        sel.open("view/%s" % self.system_2.fqdn)
        sel.click("link=Provision")
        self.failUnless(not sel.is_text_present("Schedule provision"))
        self.logout()
        self.login(user=self.admin_1,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_2.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(not sel.is_text_present(self.system_2.fqdn))
        sel.open("view/%s" % self.system_2.fqdn)
        sel.click("link=Provision")
        self.failUnless(not sel.is_text_present("Schedule provision"))
        self.logout()

    def test_available_system_2(self):
        self.login(user=self.user_3,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_2.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(sel.is_text_present(self.system_2.fqdn))
        sel.open("view/%s" % self.system_2.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))
        self.logout()
        self.login(user=self.admin_2,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_2.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(sel.is_text_present(self.system_2.fqdn))
        sel.open("view/%s" % self.system_2.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))
        self.logout()

    def test_available_system_3(self):
        self.login(user=self.user_3,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_3.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(sel.is_text_present(self.system_3.fqdn))
        sel.open("view/%s" % self.system_3.fqdn)
        sel.click("link=Provision")
        self.failUnless(sel.is_text_present("Schedule provision"))
        self.logout()

    def test_not_available_system_3(self):
        self.login(user=self.user_1,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_3.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(not sel.is_text_present(self.system_3.fqdn))
        sel.open("view/%s" % self.system_3.fqdn)
        sel.click("link=Provision")
        self.failUnless(not sel.is_text_present("Schedule provision"))
        self.logout()
        self.login(user=self.admin_1,password=self.password)
        sel = self.selenium
        sel.open('available/')
        sel.wait_for_page_to_load('30000')
        sel.select("systemsearch_0_table", "label=System/Name")
        sel.select("systemsearch_0_operation", "label=is")
        sel.type("systemsearch_0_value", "%s" % self.system_3.fqdn)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'Available Systems')
        self.failUnless(not sel.is_text_present(self.system_3.fqdn))
        sel.open("view/%s" % self.system_3.fqdn)
        sel.click("link=Provision")
        self.failUnless(not sel.is_text_present("Schedule provision"))
        self.logout()

    def tearDown(self):
        self.selenium.stop()

