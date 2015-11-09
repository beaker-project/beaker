
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import logging
import re
import requests
from turbogears.database import session
from unittest2 import SkipTest

from bkr.server.model import TaskStatus, TaskResult, RecipeTaskResult
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.assertions import assert_sorted
from bkr.inttest.server.requests_utils import post_json, patch_json, \
        login as requests_login

class TestRecipesDataGrid(WebDriverTestCase):

    log = logging.getLogger(__name__ + '.TestRecipesIndex')

    @classmethod
    def setUpClass(cls):
        # create a bunch of jobs
        with session.begin():
            cls.user = user = data_setup.create_user(password='password')
            arches = [u'i386', u'x86_64', u'ia64']
            distros = [data_setup.create_distro(name=name) for name in
                    [u'DAN5-Server-U5', u'DAN5-Client-U5', u'DAN6-U1', u'DAN6-RC3']]
            for arch in arches:
                for distro in distros:
                    distro_tree = data_setup.create_distro_tree(distro=distro, arch=arch)
                    data_setup.create_job(owner=user, distro_tree=distro_tree)
                    data_setup.create_completed_job(owner=user, distro_tree=distro_tree)

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password='password')

    # see https://bugzilla.redhat.com/show_bug.cgi?id=629147
    def check_column_sort(self, column, sort_key=None):
        b = self.browser
        b.get(get_server_base() + 'recipes/mine')
        b.find_element_by_xpath('//table[@id="widget"]/thead//th[%d]//a[@href]' % column).click()
        row_count = len(b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = [b.find_element_by_xpath('//table[@id="widget"]/tbody/tr[%d]/td[%d]' % (row, column)).text
                       for row in range(1, row_count + 1)]
        assert_sorted(cell_values, key=sort_key)

    def test_can_sort_by_whiteboard(self):
        self.check_column_sort(2)

    def test_can_sort_by_arch(self):
        self.check_column_sort(3)

    def test_can_sort_by_system(self):
        self.check_column_sort(4)

    def test_can_sort_by_status(self):
        order = ['New', 'Processed', 'Queued', 'Scheduled', 'Waiting',
                'Running', 'Completed', 'Cancelled', 'Aborted']
        self.check_column_sort(7, sort_key=lambda status: order.index(status))

    def test_can_sort_by_result(self):
        self.check_column_sort(8)

    # this version is different since the cell values will be like ['R:1', 'R:10', ...]
    def test_can_sort_by_id(self):
        column = 1
        b = self.browser
        b.get(get_server_base() + 'recipes/mine')
        b.find_element_by_xpath('//table[@id="widget"]/thead//th[%d]//a[@href]' % column).click()
        row_count = len(b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = []
        for row in range(1, row_count + 1):
            raw_value = b.find_element_by_xpath('//table[@id="widget"]/tbody/tr[%d]/td[%d]' % (row, column)).text
            m = re.match(r'R:(\d+)$', raw_value)
            assert m.group(1)
            cell_values.append(int(m.group(1)))
        assert_sorted(cell_values)

class TestRecipeView(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = user = data_setup.create_user(display_name=u'Bob Brown',
                    password='password')
            self.system_owner = data_setup.create_user()
            self.system = data_setup.create_system(owner=self.system_owner, arch=u'x86_64')
            self.distro_tree = data_setup.create_distro_tree(arch=u'x86_64')
            self.job = data_setup.create_completed_job(owner=user,
                    distro_tree=self.distro_tree, server_log=True)
            for recipe in self.job.all_recipes:
                recipe.system = self.system

        self.browser = self.get_browser()
        login(self.browser, user=user.user_name, password='password')

    def go_to_recipe_view(self, recipe):
        b = self.browser
        b.get(get_server_base() + 'recipes/mine')
        b.find_element_by_link_text(recipe.t_id).click()

    def test_recipe_systems(self):
        with session.begin():
            self.system.user = self.user
            queued_job = data_setup.create_job(owner=self.user,
                    distro_tree=self.distro_tree)
            data_setup.mark_job_queued(queued_job)
            the_recipe = queued_job.recipesets[0].recipes[0]
            the_recipe.systems[:] = [self.system]
        b = self.browser
        self.go_to_recipe_view(the_recipe)
        b.find_element_by_xpath('//td[preceding-sibling::th[text()='
            '"Possible Systems"]]/a').click()

        # Make sure our system link is there
        b.find_element_by_link_text(self.system.fqdn)
        # Make sure out user link is there
        b.find_element_by_link_text(self.system.user.user_name)
        # Make sure we only have one system against our recipe
        system_rows = b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr')
        self.assert_(len(system_rows) == 1)

    def test_log_url_looks_right(self):
        b = self.browser
        some_job = self.job
        r = some_job.recipesets[0].recipes[0]
        self.go_to_recipe_view(r)
        b.find_element_by_xpath('//div[@id="recipe%s"]//a[text()="Show Results"]' % r.id).click()
        rt_log_server_link = b.find_element_by_xpath("//tr[@class='pass_recipe_%s recipe_%s']//td[position()=4]//a" % (r.id, r.id)).get_attribute('href')
        self.assertEquals(rt_log_server_link,
                get_server_base() + 'recipes/%s/tasks/%s/logs/tasks/dummy.txt'
                % (r.id, r.tasks[0].id))
        b.find_element_by_xpath('//div[@id="recipe%s"]//button[text()="Logs"]' % r.id).click()
        r_server_link = b.find_element_by_xpath("//table/tbody//tr[position()=6]/td//a").get_attribute('href')
        self.assertEquals(r_server_link,
                get_server_base() + 'recipes/%s/logs/recipe_path/dummy.txt' % r.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1072133
    def test_watchdog_time_remaining_display(self):
        b = self.browser
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe], owner=self.user)
            data_setup.mark_job_running(job)
            recipe.watchdog.kill_time = (datetime.datetime.utcnow() +
                    datetime.timedelta(seconds=83 * 60 + 30))
        self.go_to_recipe_view(recipe)
        b.find_element_by_link_text('Show Results').click()
        duration = b.find_element_by_xpath('//tr[contains(@class, "recipe_%s")][1]'
                '//div[@class="task-duration"]' % recipe.id)
        self.assertRegexpMatches(duration.text, r'^Time Remaining 1:23:\d\d$')
        with session.begin():
            recipe.watchdog.kill_time = (datetime.datetime.utcnow() +
                    datetime.timedelta(days=2, seconds=83 * 60 + 30))
        self.go_to_recipe_view(recipe)
        duration = b.find_element_by_xpath('//tr[contains(@class, "recipe_%s")][1]'
                '//div[@class="task-duration"]' % recipe.id)
        self.assertRegexpMatches(duration.text, r'^Time Remaining 2 days, 1:23:\d\d$')

    def test_task_pagination(self):
        with session.begin():
            num_of_tasks = 35
            the_tasks = [data_setup.create_task() for t in range(num_of_tasks)]
            the_recipe = data_setup.create_recipe(task_list=the_tasks)
            the_job = data_setup.create_job_for_recipes([the_recipe], owner=self.user)

        b = self.browser
        self.go_to_recipe_view(the_recipe)
        b.find_element_by_xpath('//div[@id="recipe%s"]//a[text()="Show Results"]'
                % the_recipe.id).click()
        for t in the_job.recipesets[0].recipes[0].tasks:
            self.assertTrue(is_text_present(b, "T:%s" %t.id))

    def test_task_versions_are_shown(self):
        with session.begin():
            recipe = self.job.recipesets[0].recipes[0]
            recipetask = recipe.tasks[0]
            recipetask.version = u'1.10-23'
        b = self.browser
        self.go_to_recipe_view(recipe)
        b.find_element_by_xpath('//div[@id="recipe%s"]//a[text()="Show Results"]'
                % recipe.id).click()
        tasks_table = b.find_element_by_xpath('//div[@id="recipe%s"]'
                '//table[contains(@class, "tasks")]' % recipe.id)
        self.assertIn('1.10-23',
                tasks_table.find_element_by_xpath('//tr[td/a/text()="%s"]/td[2]'
                    % recipetask.t_id).text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=751330
    def test_fetching_large_results_is_not_too_slow(self):
        raise SkipTest('"slowness" is too subjective')
        with session.begin():
            tasks = [data_setup.create_task() for _ in range(700)]
            recipe = data_setup.create_recipe(task_list=tasks)
            for rt in recipe.tasks:
                rt.results = [RecipeTaskResult(path=u'result_%d' % i,
                        result=TaskResult.pass_, score=i) for i in range(10)]
            job = data_setup.create_job_for_recipes([recipe], owner=self.user)

        b = self.browser
        self.go_to_recipe_view(recipe)
        b.find_element_by_xpath('//div[@id="recipe%s"]//a[text()="Show Results"]'
                % recipe.id).click()
        # Let's set a wait time of 30 seconds and try to find the results table.
        # If the server is taking too long to return our results,
        # we will get a NoSuchElementException below.
        b.implicitly_wait(30)
        b.find_element_by_xpath('//div[@id="task_items_%s"]//table' % recipe.id)


    # https://bugzilla.redhat.com/show_bug.cgi?id=674025
    def test_task_anchor_on_recipe_page(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user)
            recipe = job.recipesets[0].recipes[0]
            task = recipe.tasks[0]
        b = self.browser
        # bkr/recipes/id#task<id>
        b.get(get_server_base() + 'recipes/%s#task%s' % (recipe.id, task.id))
        # "Show Results" should be activated for the recipe
        b.find_element_by_css_selector('#recipe%s .results-tab.active' % recipe.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=674025
    def test_task_anchor_on_job_page(self):
        with session.begin():
            recipes = [data_setup.create_recipe(distro_tree=self.distro_tree) for _ in range(10)]
            job = data_setup.create_job_for_recipes(recipes, owner=self.user)
        b = self.browser
        # bkr/jobs/id#task<id>
        # for multi recipe jobs, only the recipe to which the task belongs should be visible
        # choose a recipe and task somewhere in the middle
        task = job.recipesets[0].recipes[6].tasks[0].id
        recipe = recipes[6]
        b.get(get_server_base() + 'jobs/%s#task%s' %(job.id,task))
        # "Show Results" should be activated for the recipe
        b.find_element_by_css_selector('#recipe%s .results-tab.active' % recipe.id)
        recipes.remove(recipe)
        for r in recipes:
            # "Hide Results" should be activated for the recipe
            b.find_element_by_css_selector('#recipe%s .hide-results-tab.active' % r.id)

    def test_no_failed_results(self):
        with session.begin():
            the_recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([the_recipe],
                                                    owner=self.user)

        b = self.browser
        # Recipe without failed results should not show the button
        self.go_to_recipe_view(the_recipe)
        b.find_element_by_xpath(
            '//div[@id="recipe%s" and not(.//a[text()="Show Failed Results"])]'
            % the_recipe.id)

    def check_task_not_loaded(self, recipe, task):
        fmt = '//div[@id="recipe%s" and not(.//a[text()="T:%s"])]'
        self.browser.find_element_by_xpath(fmt % (recipe.id, task.id))

    def check_task_visible(self, recipe, task):
        fmt = '//div[@id="recipe%s"]//a[text()="T:%s"]'
        t = self.browser.find_element_by_xpath(fmt % (recipe.id, task.id))
        msg = "R:%s T:%s unexpectedly hidden"
        self.assertTrue(t.is_displayed(), msg % (recipe.id, task.id))

    def check_task_hidden(self, recipe, task):
        fmt = '//div[@id="recipe%s"]//a[text()="T:%s"]'
        t = self.browser.find_element_by_xpath(fmt % (recipe.id, task.id))
        msg = "R:%s T:%s unexpectedly visible"
        self.assertFalse(t.is_displayed(), msg % (recipe.id, task.id))

    def test_show_all_results(self):
        with session.begin():
            tasks = [data_setup.create_task() for t in range(5)]
            recipe = data_setup.create_recipe(task_list=tasks)
            job = data_setup.create_job_for_recipes([recipe], owner=self.user)

        b = self.browser
        self.go_to_recipe_view(recipe)
        # Tasks should only be loaded on demand
        for t in recipe.tasks:
            self.check_task_not_loaded(recipe, t)
        # Full result tab should have all tasks
        b.find_element_by_xpath(
                '//div[@id="recipe%s"]//a[text()="Show Results"]'
                % recipe.id).click()
        for t in recipe.tasks:
            self.check_task_visible(recipe, t)
        # Clicking "Hide" should hide all tasks again
        b.find_element_by_xpath(
                '//div[@id="recipe%s"]//a[text()="Hide"]'
                % recipe.id).click()
        for t in recipe.tasks:
            self.check_task_hidden(recipe, t)

    def test_show_failed_results(self):
        # To check correct display of failed results
        #   - create 3 recipes with 2 tasks each
        #   - for each recipe, mark the first task as failed in some way
        #     (Fail, Warn, Panic)
        #   - check clicking "Show Failed Results" tab shows only the first
        #   - check clicking "Hide" hides the loaded task
        status_result_pairs = []
        for result in (TaskResult.fail, TaskResult.warn, TaskResult.panic):
            for status in (TaskStatus.completed, TaskStatus.cancelled,
                            TaskStatus.aborted):
                status_result_pairs.append((status, result))

        with session.begin():
            recipes = []
            for __ in status_result_pairs:
                tasks = [data_setup.create_task() for i in range(2)]
                recipe = data_setup.create_recipe(task_list=tasks)
                recipes.append(recipe)
            job = data_setup.create_job_for_recipes(recipes, owner=self.user)
            data_setup.mark_job_queued(job)
            data_setup.mark_job_running(job)
            for recipe, (status, result) in zip(recipes, status_result_pairs):
                task_result = RecipeTaskResult(path=u'failure_result',
                                                result=result)
                recipe.tasks[0].results = [task_result]
                recipe.tasks[0].status = status
                recipe.tasks[1].start()
            job.update_status()

        b = self.browser
        for recipe in recipes:
            failed, incomplete = recipe.tasks
            expected_result = failed.results[0].result
            # These assertions ensure the task setup code above is correct
            self.assertEqual(recipe.status, TaskStatus.running)
            self.assertEqual(recipe.result, expected_result)
            self.assertEqual(failed.result, expected_result)
            self.assertEqual(incomplete.result, TaskResult.new)
            self.go_to_recipe_view(recipe)
            # Tasks should only be loaded on demand
            for t in recipe.tasks:
                self.check_task_not_loaded(recipe, t)
            # Failed result tab should only load the first task
            b.find_element_by_xpath(
                '//div[@id="recipe%s"]//a[text()="Show Failed Results"]'
                    % recipe.id).click()
            self.check_task_visible(recipe, failed)
            self.check_task_not_loaded(recipe, incomplete)
            # Clicking "Hide" should hide the loaded task
            b.find_element_by_xpath(
                    '//div[@id="recipe%s"]//a[text()="Hide"]'
                    % recipe.id).click()
            self.check_task_hidden(recipe, failed)
            self.check_task_not_loaded(recipe, incomplete)

    def test_return_system_reservation(self):
        b = self.browser
        with session.begin():
            recipe = data_setup.create_recipe(
                task_list=[data_setup.create_task()],
                reservesys=True,
                reservesys_duration=1800,
            )
            job = data_setup.create_job_for_recipes([recipe], owner=self.user)
            data_setup.mark_recipe_tasks_finished(job.recipesets[0].recipes[0])
            job.update_status()

        self.go_to_recipe_view(recipe)
        b.find_element_by_xpath('//span[@class="statusReserved"]')
        duration = b.find_element_by_xpath('//span[@class="reservation_duration"]').text
        self.assertRegexpMatches(duration, r'(0:\d\d:\d\d remaining)')
        b.find_element_by_link_text('Release System').click()
        b.find_element_by_xpath('//h1[text()="Release reserved system for Recipe %s"]' % recipe.id) 
        b.find_element_by_xpath('//form[@id="end_recipe_reservation"]//input[@type="submit"]').click()
        flash_text = b.find_element_by_class_name('flash').text
        self.assertEquals('Successfully released reserved system for %s' % recipe.t_id, 
                          flash_text)


class RecipeHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipes.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.recipe = data_setup.create_recipe()
            self.recipe_with_reservation_request = data_setup.create_recipe(reservesys=True)
            self.recipe_without_reservation_request = data_setup.create_recipe()
            self.job = data_setup.create_job_for_recipes([
                    self.recipe,
                    self.recipe_with_reservation_request,
                    self.recipe_without_reservation_request],
                    owner=self.owner)

    def test_get_recipe(self):
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['t_id'], self.recipe.t_id)

    def test_get_recipe_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
        response = requests.get(get_server_base() +
                'recipes/%s/logs/recipe_path/dummy.txt' % recipe.id,
                allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/beaker/recipe_path/dummy.txt')

    def test_404_for_nonexistent_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
        response = requests.get(get_server_base() +
                'recipes/%s/logs/doesnotexist.log' % recipe.id,
                allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        self.assertRegexpMatches(response.text, 'Recipe log .* not found')

    def test_anonymous_cannot_update_recipe(self):
        response = patch_json(get_server_base() +
                'recipes/%s' % self.recipe.id,
                data={'whiteboard': u'testwhiteboard'})
        self.assertEquals(response.status_code, 401)

    def test_can_update_recipe_whiteboard(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s' % self.recipe.id,
                session=s, data={'whiteboard': u'newwhiteboard'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe.whiteboard, 'newwhiteboard')
            self.assertEquals(self.recipe.activity[0].field_name, u'Whiteboard')
            self.assertEquals(self.recipe.activity[0].action, u'Changed')
            self.assertEquals(self.recipe.activity[0].new_value, u'newwhiteboard')

    def test_anonymous_cannot_update_reservation_request(self):
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                data={'reserve': True, 'duration': 300})
        self.assertEquals(response.status_code, 401)

    def test_cannot_update_reservation_request_on_completed_recipe(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': False})
        self.assertEquals(response.status_code, 403)

    def test_can_update_reservation_request_to_reserve_system(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        # On a recipe with reservation request
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 300})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe_with_reservation_request.reservation_request.duration,
                    300)
            self.assertEquals(self.recipe_with_reservation_request.activity[0].field_name,
                    u'Reservation Request')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].new_value,
                    u'300')
        # On a recipe without reservation request
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_without_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 300})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.recipe_without_reservation_request.reservation_request)
            self.assertEquals(self.recipe_without_reservation_request.activity[0].field_name,
                    u'Reservation Request')
            self.assertEquals(self.recipe_without_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEquals(self.recipe_without_reservation_request.activity[0].new_value,
                    u'300')

    def test_can_update_reservation_request_to_not_reserve_the_system(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': False})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertFalse(self.recipe_with_reservation_request.reservation_request)
            self.assertEquals(self.recipe_with_reservation_request.activity[0].field_name,
                    u'Reservation Request')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].new_value,
                    None)

    def test_anonymous_has_no_reviewed_state(self):
        # Reviewed state is per-user so anonymous should get "reviewed": null 
        # (neither true nor false, since we don't know).
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['reviewed'], None)

    def test_can_clear_reviewed_state(self):
        with session.begin():
            self.recipe.set_reviewed_state(self.owner, True)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'recipes/%s' % self.recipe.id,
                session=s, data={'reviewed': False})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.get_reviewed_state(self.owner), False)
