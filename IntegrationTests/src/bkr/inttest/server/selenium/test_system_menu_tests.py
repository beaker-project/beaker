
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, click_menu_item
from bkr.inttest import data_setup, get_server_base
from turbogears.database import session

class Menu(WebDriverTestCase):
    
    def setUp(self):
        with session.begin():
            data_setup.create_device(device_class="IDE")
        self.browser = self.get_browser()
        login(self.browser)

    def test_menulist(self):
        b = self.browser
        b.get(get_server_base())

        click_menu_item(b, 'Systems', 'All')
        b.find_element_by_xpath('//title[text()="Systems"]')
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Systems')
        b.find_element_by_xpath('//title[text()="My Systems"]')
        click_menu_item(b, 'Systems', 'Available')
        b.find_element_by_xpath('//title[text()="Available Systems"]')
        click_menu_item(b, 'Systems', 'Free')
        b.find_element_by_xpath('//title[text()="Free Systems"]')
        click_menu_item(b, 'Systems', 'Reserve')
        b.find_element_by_xpath('//title[text()="Reserve Workflow"]')
        click_menu_item(b, 'Devices', 'All')
        b.find_element_by_xpath('//title[text()="Devices"]')
        click_menu_item(b, 'Devices', 'IDE')
        b.find_element_by_xpath('//title[text()="Devices"]')
        click_menu_item(b, 'Distros', 'Family')
        b.find_element_by_xpath('//title[text()="OS Versions"]')
        click_menu_item(b, 'Scheduler', 'New Job')
        b.find_element_by_xpath('//title[text()="New Job"]')
        click_menu_item(b, 'Scheduler', 'Watchdog')
        b.find_element_by_xpath('//title[text()="Watchdogs"]')
        click_menu_item(b, 'Activity', 'All')
        b.find_element_by_xpath('//title[text()="Activity"]')
        click_menu_item(b, 'Activity', 'Systems')
        b.find_element_by_xpath('//title[text()="System Activity"]')
        click_menu_item(b, 'Activity', 'Distros')
        b.find_element_by_xpath('//title[text()="Distro Activity"]')
