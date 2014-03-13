
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.webdriver_utils import is_text_present
import unittest
from turbogears.database import session

class TaskByName(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.my_task = data_setup.create_task()
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_task_redirect(self):
        b = self.browser
        task_id = self.my_task.id
        task_name = self.my_task.name

        b.get(get_server_base() + 'tasks%s' % task_name)
        self.assert_('Task %s' % task_name in b.find_element_by_xpath('//body').text)

        b.get(get_server_base() + 'tasks/%s' % task_id)
        self.assert_('Task %s' % task_name in b.find_element_by_xpath('//body').text)
