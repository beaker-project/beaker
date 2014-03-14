# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from turbogears.database import session
from bkr.server.model import CommandActivity, CommandStatus
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base


class GridTest(WebDriverTestCase):
    #    This test class assumes a couple of things:
    #
    #      2) The number of rows returned per page on the System activity tab is 50
    #      3) This number cannot be modified by using tg_paginate_limit

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system()
            user = data_setup.create_user()
            self.activity = CommandActivity(user, 'Just', 'testing',
                status=CommandStatus.queued)
            self.system.command_queue.append(self.activity)
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def _get_paginators(self):
        b = self.browser
        paginators = b.find_elements_by_class_name('pagination')
        if not paginators:
            raise AssertionError('Could not find pagination links')
        return paginators

    def create_activity_pages(self, number_of_pages):
        with session.begin():
            for i in range(50 * number_of_pages):
                self.activity.log_to_system_history()

    def check_paginate_links_not_there(self):
        b = self.browser
        paginators = self._get_paginators()
        for p in paginators:
            p.find_element_by_xpath('div[@class="pagination-beside" '
                'and not(..//ul)]')

    def check_page_text_is_shown(self, page_text, current=False):
        b = self.browser
        if current:
            page_xpath = u"ul/li/span[normalize-space(text())='%s']" % page_text
        else:
            page_xpath = u"ul/li/a[normalize-space(text())='%s']" % page_text

        paginators = self._get_paginators()
        for p in paginators:
            p.find_element_by_xpath(page_xpath)

    def click_page_number(self, page_text):
        b = self.browser
        b.find_element_by_xpath(u'//div[@class="pagination'
            ' pagination-right"]/ul/li/a[text()="%s"]' % page_text).click()

    def go_to_system_activity(self):
        b = self.browser
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_link_text('Show Search Options').click()
        Select(b.find_element_by_id('activitysearch_0_table')). \
            select_by_visible_text('System/Name')
        Select(b.find_element_by_id('activitysearch_0_operation')). \
            select_by_visible_text('is')
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']"). \
            send_keys(self.system.fqdn)
        b.find_element_by_id('searchform').submit()

    def test_no_pagination_with_single_page(self):
        self.create_activity_pages(1)
        self.go_to_system_activity()
        self.check_paginate_links_not_there()

    def test_pagination_links_exist_with_five_pages(self):
        self.create_activity_pages(5)
        self.go_to_system_activity()
        for number in range(1,6):
            self.check_page_text_is_shown(number, True if number is 1 else False)

    def test_no_ellipsis_with_six_pages(self):
        # We're expecting 1 2 3 4 5 6 and no ellipsis.
        b = self.browser
        self.create_activity_pages(6)
        self.go_to_system_activity()
        # Start clicking from page #2
        for number in range(2,7):
            self.click_page_number(number)
            one_is_current=False
            six_is_current=False
            if number is 1:
                one_is_current = True
            if number is 6:
                six_is_current = True
            self.check_page_text_is_shown(1, one_is_current)
            self.check_page_text_is_shown(6, six_is_current)

    def test_min_count_of_two_between_ends_of_ellipsis(self):
        # Checking for the following
        # _1 2 3 4 5...8
        # 1 2 3 _4 5...8
        # 1...3 4 _5 6 7 8
        self.create_activity_pages(8)
        self.go_to_system_activity()
        # We will be on page 1...
        self.check_page_text_is_shown(u'…8')

        self.click_page_number('4')
        self.check_page_text_is_shown(u'…8')
        self.check_page_text_is_shown('1')

        self.click_page_number('5')
        self.check_page_text_is_shown(u'1…')
        self.check_page_text_is_shown('8')
