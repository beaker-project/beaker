
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, click_menu_item
from bkr.inttest import data_setup, with_transaction, get_server_base

class ItemCount(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.browser = self.get_browser()
        data_setup.create_device(device_class="IDE") #needed for device page
        data_setup.create_distro() # needed for distro page
        data_setup.create_job() # needed for job page
        data_setup.create_task() #create task
        system = data_setup.create_system(shared=True)
        system.activity.append(data_setup.create_system_activity())

    def test_itemcount(self):
        b = self.browser
        login(b)
        b.get(get_server_base())
        click_menu_item(b, 'Systems', 'All')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
        click_menu_item(b, 'Systems', 'Available')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
        click_menu_item(b, 'Systems', 'Free')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
        click_menu_item(b, 'Devices', 'All')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
        click_menu_item(b, 'Distros', 'All')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
        click_menu_item(b, 'Scheduler', 'Jobs')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
        click_menu_item(b, 'Scheduler', 'Task Library')
        b.find_element_by_xpath('//span[contains(text(), "Items found:")]')
