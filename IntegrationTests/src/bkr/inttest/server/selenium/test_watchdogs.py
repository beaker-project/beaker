
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.server.model import TaskStatus
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase

class WatchdogsTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_page_works(self):
        # make sure we have at least one watchdog to see
        with session.begin():
            data_setup.mark_job_running(data_setup.create_job())
        b = self.browser
        b.get(get_server_base() + 'watchdogs/')
        self.assertEquals(b.title, 'Watchdogs')

    # https://bugzilla.redhat.com/show_bug.cgi?id=849818
    def test_handles_null_recipe_task_id(self):
        with session.begin():
            dt = data_setup.create_distro_tree()
            running_recipe = data_setup.create_recipe(distro_tree=dt)
            waiting_recipe = data_setup.create_recipe(distro_tree=dt)
            job = data_setup.create_job_for_recipes(
                    [running_recipe, waiting_recipe])
            data_setup.mark_recipe_running(running_recipe)
            data_setup.mark_recipe_waiting(waiting_recipe)
            self.assertEquals(waiting_recipe.watchdog.recipetask, None)
        b = self.browser
        b.get(get_server_base() + 'watchdogs/')
        self.assertEquals(b.title, 'Watchdogs')
