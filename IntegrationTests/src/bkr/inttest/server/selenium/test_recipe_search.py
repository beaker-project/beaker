
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.webdriver_utils import check_recipe_search_results
from turbogears.database import session

class SearchRecipes(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.running_job = data_setup.create_job()
            self.queued_job = data_setup.create_job()
            self.completed_job = data_setup.create_completed_job()
            data_setup.mark_job_queued(self.queued_job)
            data_setup.mark_job_running(self.running_job)
            self.running_recipe = self.running_job.recipesets[0].recipes[0]
            self.queued_recipe = self.queued_job.recipesets[0].recipes[0]
            self.completed_recipe = self.completed_job.recipesets[0].recipes[0]
        self.browser = self.get_browser()

    def test_quick_search(self):
        b = self.browser
        b.get(get_server_base() + 'recipes/')
        # Test Queued and only Queued recipe is shown
        b.find_element_by_xpath("//button[@value='Status-is-Queued']").click()
        check_recipe_search_results(b, present=[self.queued_recipe],
                absent=[self.running_recipe, self.completed_recipe])

        # Test Running and only Running recipe is shown
        b.find_element_by_xpath("//button[@value='Status-is-Running']").click()
        check_recipe_search_results(b, present=[self.running_recipe],
                absent=[self.queued_recipe, self.completed_recipe])

        # Test Completed and only Completed recipe is shown
        b.find_element_by_xpath("//button[@value='Status-is-Completed']").click()
        check_recipe_search_results(b, present=[self.completed_recipe],
                absent=[self.running_recipe, self.queued_recipe])
