
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, click_menu_item
from bkr.inttest import data_setup, get_server_base

class Menu(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_my_menu(self):
        b = self.browser
        login(b)
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Jobs')
        b.find_element_by_xpath('//title[text()="My Jobs"]')
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Recipes')
        b.find_element_by_xpath('//title[text()="Recipes"]')
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Systems')
        b.find_element_by_xpath('//title[text()="My Systems"]')
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Groups')
        b.find_element_by_xpath('//title[text()="Groups"]')
        self.assertEqual(
            b.find_element_by_class_name('search-query').get_attribute('value'),
            'member.user_name:%s' % data_setup.ADMIN_USER)
