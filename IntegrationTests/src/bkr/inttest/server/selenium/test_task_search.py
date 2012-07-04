#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, with_transaction, get_server_base
import unittest, time, re, os
from turbogears.database import session


class TaskSearchWD(WebDriverTestCase):

    @classmethod
    @with_transaction
    def setupClass(cls):
        with session.begin():
            cls.task_one = data_setup.create_task(
                name=data_setup.unique_name(u'/a/a/a%s'))

    def setUp(self):
        self.browser = self.get_browser()

    @with_transaction
    def test_executed_tasks(self):
        with session.begin():
            self.job = data_setup.create_completed_job(task_name=self.task_one.name)
        b = self.browser
        b.get(get_server_base() + 'tasks/%d' % self.task_one.id)
        r = self.job.recipesets[0].recipes[0]
        b.find_element_by_xpath("//select[@name='osmajor_id']/"
            "option[normalize-space(text())='%s']" %
             r.distro_tree.distro.osversion.osmajor).click()
        b.find_element_by_xpath("//form[@id='form']").submit()
        b.find_element_by_xpath("//div[@id='task_items']//"
            "a[normalize-space(text())='%s']" % r.tasks[0].t_id)


class Search(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.arch_one = u'i386'
        self.osmajor_one = u'testosmajor'
        self.task_one = data_setup.create_task(name=u'/a/a/a', exclude_arch=[self.arch_one])
        self.task_two = data_setup.create_task(name=u'/a/a/b', exclude_arch=[self.arch_one])
        self.task_three = data_setup.create_task(name=u'/a/a/c', exclude_osmajor=[self.osmajor_one])
        self.selenium.start()

    def test_task_deleted(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            r = data_setup.create_recipe(task_name=self.task_three.name)
            j = data_setup.create_job_for_recipes((r,), owner=user)

        sel = self.selenium
        self.login(user=user.user_name, password=u'password')
        sel.open(u'tasks%s' % self.task_three.name)
        sel.wait_for_page_to_load('30000')
        sel.click("//input[@type='submit']")
        self.wait_and_try(lambda: self.assert_(sel.is_text_present(u"T:%s" % r.tasks[0].id)), wait_time=10)

        with session.begin():
            j.soft_delete()
        sel.open(u'tasks%s' % self.task_three.name)
        sel.wait_for_page_to_load('30000')
        sel.click("//input[@type='submit']")
        try:
            self.wait_and_try(lambda: self.assert_(sel.is_text_present(u"T:%s" % r.tasks[0].id)), wait_time=10)
        except AssertionError:
            pass
        else:
            raise AssertionError(u'Found task %s where it was deleted and should not be viewable' % self.task_three.id)



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
