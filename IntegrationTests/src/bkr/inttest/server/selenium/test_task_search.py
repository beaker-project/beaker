#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, with_transaction, get_server_base
import unittest, time, re, os
from turbogears.database import session
from bkr.server.model import OSMajor


class ExecutedTasksTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def check_recipetask_present_in_results(self, recipetask):
        return self.browser.find_element_by_xpath("//div[@id='task_items']//"
                "a[normalize-space(text())='%s']" % recipetask.t_id)

    def test_executed_tasks(self):
        with session.begin():
            task_two = data_setup.create_task(name=data_setup.unique_name(u'/a/a/a%s'))
            task_one = data_setup.create_task(name=data_setup.unique_name(u'/a/a/a%s'))
            job = data_setup.create_completed_job(task_list=[task_one, task_two])
        b = self.browser
        r = job.recipesets[0].recipes[0]
        rtask = r.tasks[0]
        b.get(get_server_base() + 'tasks/%d' % rtask.task.id)
        b.find_element_by_xpath("//select[@name='osmajor_id']/"
            "option[normalize-space(text())='%s']" %
             r.distro_tree.distro.osversion.osmajor).click()
        b.find_element_by_xpath("//form[@id='form']").submit()
        self.check_recipetask_present_in_results(rtask)

        # Search by single recipe task id
        b.get(get_server_base() + 'tasks/executed?recipe_task_id=%s' % rtask.id)
        self.check_recipetask_present_in_results(rtask)

        # Search by multiple recipe task id
        rtask2 = r.tasks[1]
        b.get(get_server_base() + 'tasks/executed?recipe_task_id=%s&recipe_task_id=%s' % (rtask2.id, rtask.id))
        self.check_recipetask_present_in_results(rtask)
        self.check_recipetask_present_in_results(rtask2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=840720
    def test_executed_tasks_family_sorting(self):
        with session.begin():
            task = data_setup.create_task()
            data_setup.create_completed_job(task_name=task.name,
                    distro_tree=data_setup.create_distro_tree(osmajor=u'BlueShoe10'))
            data_setup.create_completed_job(task_name=task.name,
                    distro_tree=data_setup.create_distro_tree(osmajor=u'BlueShoe9'))
            # plus one that is never used
            OSMajor.lazy_create(osmajor=u'neverused666')
        b = self.browser
        b.get(get_server_base() + 'tasks/%d' % task.id)
        options = [element.text for element in
                b.find_elements_by_xpath("//select[@name='osmajor_id']/option")]
        self.assert_(options.index('BlueShoe9') < options.index('BlueShoe10'), options)
        self.assert_('neverused666' not in options, options)

    def test_executed_tasks_system_filter(self):
        with session.begin():
            task = data_setup.create_task()
            system = data_setup.create_system(
                    lab_controller=data_setup.create_labcontroller())
            job = data_setup.create_completed_job(task_name=task.name,
                    system=system)
        b = self.browser
        b.get(get_server_base() + 'tasks/%d' % task.id)
        b.find_element_by_id('form_system').click()
        b.find_element_by_id('form_system').send_keys(system.fqdn)
        b.find_element_by_id('form').submit()
        rtask = job.recipesets[0].recipes[0].tasks[0]
        self.check_recipetask_present_in_results(rtask)

    def test_executed_tasks_guest_filter(self):
        with session.begin():
            task = data_setup.create_task()
            fqdn = 'test_executed_tasks_guest_fqdn_filter.invalid'
            distro_tree = data_setup.create_distro_tree()
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            guestrecipe = data_setup.create_guestrecipe(host=recipe,
                    task_name=task.name, distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe, guestrecipe])
            data_setup.mark_recipe_running(recipe)
            data_setup.mark_recipe_running(guestrecipe, fqdn=fqdn)
        b = self.browser
        b.get(get_server_base() + 'tasks/%d' % task.id)
        b.find_element_by_id('form_system').click()
        b.find_element_by_id('form_system').send_keys(fqdn)
        b.find_element_by_id('form').submit()
        self.check_recipetask_present_in_results(guestrecipe.tasks[0])

class Search(SeleniumTestCase):

    @with_transaction
    def setUp(self):
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

    def assert_task_in_results(self, task):
        self.assert_(self.selenium.is_element_present(
                '//table[@id="widget"]//td[1][.//text()="%s"]' % task.name))

    def assert_task_not_in_results(self, task):
        self.assert_(not self.selenium.is_element_present(
                '//table[@id="widget"]//td[1][.//text()="%s"]' % task.name))

    def test_task_search(self):
        sel = self.selenium
        sel.open('tasks')
        sel.wait_for_page_to_load("30000")
        sel.select("tasksearch_0_table", "label=Arch")  
        sel.select("tasksearch_0_operation", "label=is")
        sel.type("tasksearch_0_value", "%s" % self.arch_one)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load("30000") 
        self.assert_task_in_results(self.task_three)
        self.assert_task_not_in_results(self.task_two)
        self.assert_task_not_in_results(self.task_one)

        sel.select("tasksearch_0_table", "label=Arch")  
        sel.select("tasksearch_0_operation", "label=is not")
        sel.type("tasksearch_0_value", "%s" % self.arch_one)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load("30000")
        self.assert_task_not_in_results(self.task_three)
        self.assert_task_in_results(self.task_two)
        self.assert_task_in_results(self.task_one)

        sel.select("tasksearch_0_table", "label=Distro")  
        sel.select("tasksearch_0_operation", "label=is")
        sel.type("tasksearch_0_value", "%s" % self.osmajor_one)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load("30000")
        self.assert_task_not_in_results(self.task_three)
        self.assert_task_in_results(self.task_two)
        self.assert_task_in_results(self.task_one)

        sel.select("tasksearch_0_table", "label=Distro")  
        sel.select("tasksearch_0_operation", "label=is not")
        sel.type("tasksearch_0_value", "%s" % self.osmajor_one)
        sel.submit('id=searchform')
        sel.wait_for_page_to_load("30000")
        self.assert_task_in_results(self.task_three)
        self.assert_task_not_in_results(self.task_two)
        self.assert_task_not_in_results(self.task_one)

    def tearDown(self):
        self.selenium.stop()
