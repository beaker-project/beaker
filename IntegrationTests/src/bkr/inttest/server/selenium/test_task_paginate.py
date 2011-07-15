#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
from turbogears.database import session
from datetime import datetime

class TaskPaginate(SeleniumTestCase):

    @classmethod
    def setupClass(cls):
        num_of_tasks = 35
        cls.the_tasks= [data_setup.create_task() for t in range(num_of_tasks)]
        cls.the_recipe = data_setup.create_recipe(task_list=cls.the_tasks)
        cls.the_job = data_setup.create_job_for_recipes([cls.the_recipe])
        cls.selenium = cls.get_selenium()
        cls.selenium.start()
        session.flush()

    def test_task_pagination(self):
        sel = self.selenium
        sel.open('recipes/%s' % self.the_recipe.id)
        sel.click("all_recipe_%s" % self.the_recipe.id)
        def _look_for_tasks():
            for t in self.the_job.recipesets[0].recipes[0].tasks:
                self.assertTrue(sel.is_text_present("T:%s" %t.id))
                print t.id
        self.wait_and_try(_look_for_tasks)

    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()

