
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import check_task_search_results
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from turbogears.database import session
from bkr.server.model import OSMajor
from bkr.server.tasks import Tasks

class ExecutedTasksTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def check_recipetask_present_in_results(self, recipetask):
        return self.browser.find_element_by_xpath("//div[@id='task_items']//"
                "a[normalize-space(text())='%s']" % recipetask.t_id)

    def check_recipetask_absent_from_results(self, recipetask):
        return self.browser.find_element_by_xpath("//div[@id='task_items' and "
                "not(.//a[normalize-space(text())='%s'])]" % recipetask.t_id)

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

    def test_task_deleted(self):
        with session.begin():
            task = data_setup.create_task()
            recipe = data_setup.create_recipe(task_name=task.name)
            job = data_setup.create_job_for_recipes([recipe])
        b = self.browser
        b.get(get_server_base() + 'tasks%s' % task.name)
        b.find_element_by_id('form').submit()
        self.check_recipetask_present_in_results(recipe.tasks[0])

        with session.begin():
            job.deleted = datetime.datetime.utcnow()
        b.get(get_server_base() + 'tasks%s' % task.name)
        b.find_element_by_id('form').submit()
        self.check_recipetask_absent_from_results(recipe.tasks[0])

    def test_search_by_version(self):
        with session.begin():
            task = data_setup.create_task()
            old_recipe = data_setup.create_recipe(task_list=[task])
            data_setup.create_job_for_recipes([old_recipe])
            old_recipe.tasks[0].version = u'1.0-0'
            recent_recipe = data_setup.create_recipe(task_list=[task])
            data_setup.create_job_for_recipes([recent_recipe])
            recent_recipe.tasks[0].version = u'2.3-4'
        b = self.browser
        b.get(get_server_base() + 'tasks%s' % task.name)
        b.find_element_by_id('form_version').send_keys('1.0-*')
        b.find_element_by_id('form').submit()
        self.check_recipetask_present_in_results(old_recipe.tasks[0])
        self.check_recipetask_absent_from_results(recent_recipe.tasks[0])

class Search(WebDriverTestCase):

    @classmethod
    def setUpClass(cls):
        with session.begin():
            cls.arch_one = u'i386'
            cls.osmajor_one = u'testosmajor'
            cls.task_one = data_setup.create_task(name=u'/a/a/a', exclude_arches=[cls.arch_one])
            cls.task_two = data_setup.create_task(name=u'/a/a/b', exclude_arches=[cls.arch_one])
            cls.task_three = data_setup.create_task(name=u'/a/a/c', exclude_osmajors=[cls.osmajor_one])

    def setUp(self):
        self.browser = self.get_browser()

    def test_excluded_arch_is(self):
        b = self.browser
        b.get(get_server_base() + 'tasks')
        b.find_element_by_class_name('search-query').send_keys('excluded_arch:%s' % self.arch_one)
        b.find_element_by_class_name('grid-filter').submit()
        check_task_search_results(b, absent=[self.task_three],
                present=[self.task_one, self.task_two])

    def test_excluded_arch_is_not(self):
        b = self.browser
        b.get(get_server_base() + 'tasks')
        b.find_element_by_class_name('search-query').send_keys('-excluded_arch:%s' % self.arch_one)
        b.find_element_by_class_name('grid-filter').submit()
        check_task_search_results(b, absent=[self.task_one, self.task_two],
                present=[self.task_three])

    def test_osmajor_excluded_is(self):
        b = self.browser
        b.get(get_server_base() + 'tasks')
        b.find_element_by_class_name('search-query').send_keys('excluded_osmajor:%s' % self.osmajor_one)
        b.find_element_by_class_name('grid-filter').submit()
        check_task_search_results(b, absent=[self.task_one, self.task_two],
                present=[self.task_three])

    def test_osmajor_excluded_is_not(self):
        b = self.browser
        b.get(get_server_base() + 'tasks')
        b.find_element_by_class_name('search-query').send_keys('-excluded_osmajor:%s' % self.osmajor_one)
        b.find_element_by_class_name('grid-filter').submit()
        check_task_search_results(b, absent=[self.task_three],
                present=[self.task_one, self.task_two])



class TaskSearchControllerTest(DatabaseTestCase):

    def get_task_query(self, kw, filter_on_recipe_task_ids=True):
        t = Tasks()
        if filter_on_recipe_task_ids:
            kw['recipe_task_id'] = [r.id for r in self.recipe_tasks]
        ret = t._do_search({}, **kw)
        return ret['tasks']

    def assert_result_counts_match(self, search_key, items):
        for [id, count] in [[x, items.count(x)] for x in set(items)]:
            query = self.get_task_query({search_key: id})
            self.assertEqual(count, query.count())

    # Tests to ensure there are no regressions from query refactor
    # https://bugzilla.redhat.com/show_bug.cgi?id=1224848
    def test_search_api_directly(self):
        with session.begin():
            self.arch_one = u'i386'
            self.osmajor_one = u'testosmajor'
            self.task_one = data_setup.create_task(name=u'/a/b/a', exclude_arches=[self.arch_one])
            self.task_two = data_setup.create_task(name=u'/a/b/b', exclude_arches=[self.arch_one])
            self.task_three = data_setup.create_task(name=u'/a/b/c', exclude_osmajors=[self.osmajor_one])
            data_setup.create_completed_job(task_list=[self.task_one, self.task_two, self.task_three])
            self.recipe_tasks = []
            for id in [t.id for t in [self.task_one, self.task_two, self.task_three]]:
                self.recipe_tasks.extend(self.get_task_query({'task_id': id}, False).all())

        all_tasks = self.recipe_tasks
        self.assertEqual(3, len(all_tasks))

        self.assert_result_counts_match('distro_tree_id', [t.recipe.distro_tree.id for t in all_tasks])
        self.assert_result_counts_match('distro_id', [t.recipe.distro_tree.distro.id for t in all_tasks])
        self.assert_result_counts_match('distro', [t.recipe.distro_tree.distro.name for t in all_tasks])
        self.assert_result_counts_match('arch_id', [t.recipe.distro_tree.arch_id for t in all_tasks])
        self.assert_result_counts_match('task_id', [t.task_id for t in all_tasks])
        self.assert_result_counts_match('task', [t.name for t in all_tasks])
        self.assert_result_counts_match('status', [t.status for t in all_tasks])
        self.assert_result_counts_match('result', [t.result for t in all_tasks])
        self.assert_result_counts_match('osmajor_id', [t.recipe.distro_tree.distro.osversion.osmajor_id for t in all_tasks])

        self.assertEqual(0, self.get_task_query({'is_failed': True}).count())

        self.assertEqual(0, self.get_task_query({'whiteboard': 'foo'}).count())
        self.assertEqual(3, self.get_task_query({'whiteboard': None}).count())

        system = all_tasks[0].recipe.resource.system
        self.assertEqual(3, self.get_task_query({'system': system.fqdn}).count())
        self.assertEqual(3, self.get_task_query({'system_id': system.id}).count())
