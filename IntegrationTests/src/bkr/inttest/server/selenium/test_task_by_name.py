
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.webdriver_utils import is_text_present
import unittest
from turbogears.database import session
import requests

class TaskByName(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.my_task = data_setup.create_task()
        self.browser = self.get_browser()

    def test_task_redirect(self):
        b = self.browser
        task_id = self.my_task.id
        task_name = self.my_task.name

        b.get(get_server_base() + 'tasks%s' % task_name)
        self.assert_('Task %s' % task_name in b.find_element_by_xpath('//body').text)

        b.get(get_server_base() + 'tasks/%s' % task_id)
        self.assert_('Task %s' % task_name in b.find_element_by_xpath('//body').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1614171
    def test_task_404_by_name(self):
        task_name_without_slash = 'no/such/name/exists/in/our/database'
        task_name_with_slash = '/%s' % task_name_without_slash

        # testing name 404 without slash
        response = requests.get(get_server_base() + 'tasks/%s/' % task_name_without_slash)
        self.assertEqual(response.status_code, 404)

        # testing name 404 with starting slash
        response = requests.get(get_server_base() + 'tasks/%s/' % task_name_with_slash)
        self.assertEqual(response.status_code, 404)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1614171
    # Searching for ID returns human friendly error as well as 404
    def test_task_404_by_id(self):
        task_id = 123456789099999

        response = requests.get(get_server_base() + 'tasks/%s' % task_id)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, 'No such task with ID: %s' % task_id)
