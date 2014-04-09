
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session


class SearchRecipes(SeleniumTestCase):


    @classmethod
    @with_transaction
    def setUpClass(cls):
        cls.running_job = data_setup.create_job()
        cls.queued_job = data_setup.create_job()
        cls.completed_job = data_setup.create_completed_job()
        data_setup.mark_job_queued(cls.queued_job)
        data_setup.mark_job_running(cls.running_job)
        cls.selenium = cls.get_selenium()
        cls.selenium.start()

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()

    def test_quick_search(self):
        sel = self.selenium
        sel.open('recipes')
        sel.wait_for_page_to_load("30000")
        # Test Queued and only Queued recipe is shown
        sel.click("//button[@value='Status-is-Queued']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_text("//table[@id='widget']/tbody/tr[1]/td[1]"),
                'R:%s' % self.queued_job.recipesets[0].recipes[0].id)
        queued_table_text = sel.get_text("//table[@id='widget']")
        self.assert_('R:%s' % self.running_job.recipesets[0].recipes[0].id not in queued_table_text)
        self.assert_('R:%s' % self.completed_job.recipesets[0].recipes[0].id not in queued_table_text)

        # Test Running and only Running recipe is shown
        sel.click("//button[@value='Status-is-Running']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_text("//table[@id='widget']/tbody/tr[1]/td[1]"),
                'R:%s' % self.running_job.recipesets[0].recipes[0].id)
        running_table_text = sel.get_text("//table[@id='widget']")
        self.assert_('R:%s' % self.queued_job.recipesets[0].recipes[0].id not in running_table_text)
        self.assert_('R:%s' % self.completed_job.recipesets[0].recipes[0].id not in running_table_text)

        # Test Completed and only Completed recipe is shown
        sel.click("//button[@value='Status-is-Completed']")
        sel.wait_for_page_to_load("30000")
        self.assertEqual(sel.get_text("//table[@id='widget']/tbody/tr[1]/td[1]"),
                'R:%s' % self.completed_job.recipesets[0].recipes[0].id)
        completed_table_text = sel.get_text("//table[@id='widget']")
        self.assert_('R:%s' % self.running_job.recipesets[0].recipes[0].id not in completed_table_text)
        self.assert_('R:%s' % self.queued_job.recipesets[0].recipes[0].id not in completed_table_text)




