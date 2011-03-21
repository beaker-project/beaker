#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class Search(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.arch_one = u'i386'
        self.osmajor_one = u'testosmajor'
        self.task_one = data_setup.create_task(name=u'/a/a/a', exclude_arch=[self.arch_one])
        self.task_two = data_setup.create_task(name=u'/a/a/b', exclude_arch=[self.arch_one])
        self.task_three = data_setup.create_task(name=u'/a/a/c', exclude_osmajor=[self.osmajor_one])
        session.flush()
        self.selenium.start()

    def test_task_search(self):
        sel = self.selenium
        sel.open('tasks')
        sel.wait_for_page_to_load("30000")
        sel.select("tasksearch_0_table", "label=Arch")  
        sel.select("tasksearch_0_operation", "label=is")
        sel.type("tasksearch_0_value", "%s" % self.arch_one)
        sel.click("Search")
        sel.wait_for_page_to_load("30000") 
        try: self.failUnless(sel.is_text_present("%s" % self.task_three.name))
        except AssertionError, e: self.verificationErrors.append(unicode('1.Did not find %s' % self.task_three.name))
        try: self.failUnless(not sel.is_text_present("%s" % self.task_two.name))
        except AssertionError, e: self.verificationErrors.append(unicode("2. Found %s where it shouldn't have been" % self.task_two.name))
        try: self.failUnless(not sel.is_text_present("%s" % self.task_one.name))
        except AssertionError, e: self.verificationErrors.append(unicode("3. Found %s where it shouldn't have been" % self.task_one.name))

        sel.select("tasksearch_0_table", "label=Arch")  
        sel.select("tasksearch_0_operation", "label=is not")
        sel.type("tasksearch_0_value", "%s" % self.arch_one)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("%s" % self.task_three.name))
        except AssertionError, e: self.verificationErrors.append(unicode("4.Found %s where it shouldn't have been" % self.task_three.name))
        try: self.failUnless(sel.is_text_present("%s" % self.task_two.name))
        except AssertionError, e: self.verificationErrors.append(unicode("5.Did not find %s " % self.task_two.name))
        try: self.failUnless(sel.is_text_present("%s" % self.task_one.name))
        except AssertionError, e: self.verificationErrors.append(unicode("6.Did not find %s" % self.task_one.name))

        sel.select("tasksearch_0_table", "label=Distro")  
        sel.select("tasksearch_0_operation", "label=is")
        sel.type("tasksearch_0_value", "%s" % self.osmajor_one)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(not sel.is_text_present("%s" % self.task_three.name))
        except AssertionError, e: self.verificationErrors.append(unicode("7.Found %s where it shouldn't have been" % self.task_three.name))
        try: self.failUnless(sel.is_text_present("%s" % self.task_two.name))
        except AssertionError, e: self.verificationErrors.append(unicode("8.Did not find %s " % self.task_two.name))
        try: self.failUnless(sel.is_text_present("%s" % self.task_one.name))
        except AssertionError, e: self.verificationErrors.append(unicode("9.Did not find %s" % self.task_one.name))
        #import pdb;pdb.set_trace()

        sel.select("tasksearch_0_table", "label=Distro")  
        sel.select("tasksearch_0_operation", "label=is not")
        sel.type("tasksearch_0_value", "%s" % self.osmajor_one)
        sel.click("Search")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("%s" % self.task_three.name))
        except AssertionError, e: self.verificationErrors.append(unicode("10.Did not find" % self.task_three.name))
        try: self.failUnless(not sel.is_text_present("%s" % self.task_two.name))
        except AssertionError, e: self.verificationErrors.append(unicode("11.Found %s where it shouldn't have been" % self.task_two.name))
        try: self.failUnless(not sel.is_text_present("%s" % self.task_one.name))
        except AssertionError, e: self.verificationErrors.append(unicode("12.Found %s where it shouldn't have been" % self.task_one.name))

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
