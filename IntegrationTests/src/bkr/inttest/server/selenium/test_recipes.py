# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import unittest
import logging
import re
from turbogears.database import session
from nose.plugins.skip import SkipTest

from bkr.server.model import Job, TaskResult, RecipeTaskResult
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present
from selenium.webdriver.support.ui import WebDriverWait
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.assertions import assert_sorted

class TestRecipesDataGrid(SeleniumTestCase):

    log = logging.getLogger(__name__ + '.TestRecipesIndex')

    # tests in this class can safely share the same firefox session
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

        cls.selenium = sel = cls.get_selenium()
        sel.start()

        # log in
        sel.open('')
        sel.click('link=Log in')
        sel.wait_for_page_to_load('30000')
        sel.type('user_name', user.user_name)
        sel.type('password', 'password')
        sel.click('login')
        sel.wait_for_page_to_load('30000')

    @classmethod
    def tearDownClass(cls):
        cls.selenium.stop()

    # see https://bugzilla.redhat.com/show_bug.cgi?id=629147
    def check_column_sort(self, column, sort_key=None):
        sel = self.selenium
        sel.open('recipes/mine')
        sel.click('//table[@id="widget"]/thead//th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = [sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[%d]' % (row, column))
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
        sel = self.selenium
        sel.open('recipes/mine')
        sel.click('//table[@id="widget"]/thead//th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = []
        for row in range(1, row_count + 1):
            raw_value = sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[%d]' % (row, column))
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

    def tearDown(self):
        self.browser.quit()

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
        self.assertEquals(rt_log_server_link, 'http://dummy-archive-server/beaker/tasks/dummy.txt')
        b.find_element_by_xpath('//div[@id="recipe%s"]//button[text()="Logs"]' % r.id).click()
        r_server_link = b.find_element_by_xpath("//table/tbody//tr[position()=6]/td//a").get_attribute('href')
        self.assertEquals(r_server_link, 'http://dummy-archive-server/beaker/recipe_path/dummy.txt')

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
    def test_task_anchor(self):
        with session.begin():
            recipes = [data_setup.create_recipe(distro_tree=self.distro_tree) for _ in range(10)]
            job = data_setup.create_job_for_recipes(recipes, owner=self.user)

        b = self.browser
        recipe = recipes[0]
        task = job.recipesets[0].recipes[0].tasks[0].id
        # bkr/recipes/id#task<id>
        b.get(get_server_base() + 'recipes/%s#task%s' %(recipe.id,task))
        # "Show Results" should be activated for the recipe
        b.find_element_by_css_selector('#recipe%s .results-tab.active' % recipe.id)

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
