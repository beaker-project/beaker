# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from turbogears.database import session
from bkr.server.model import User
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base


class GridTest(WebDriverTestCase):

    def setUp(self):
        self.page_size = 20
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            other_lc = data_setup.create_labcontroller()
            for _ in range(self.page_size + 5):
                other_lc.record_activity(service=u'testdata',
                        field=u'nothing', action=u'nothing')
        self.browser = self.get_browser()

    def _get_paginators(self):
        b = self.browser
        paginators = b.find_elements_by_class_name('pagination')
        if not paginators:
            raise AssertionError('Could not find pagination links')
        return paginators

    def create_activity_pages(self, number_of_pages):
        with session.begin():
            user = User.query.first()
            for i in range(self.page_size * number_of_pages):
                self.lc.record_activity(user=user, service=u'testdata',
                        field=u'nonsense', action=u'poke')

    def check_page_text_is_shown(self, page_text, current=False):
        b = self.browser
        if current:
            page_xpath = u"span[normalize-space(text())='%s']" % page_text
        else:
            page_xpath = u"a[normalize-space(text())='%s']" % page_text
        try:
            b.find_element_by_xpath(u'//div[contains(@class, "pagination")]/ul/li/'
                    + page_xpath)
        except NoSuchElementException:
            raise AssertionError('Expected to find page element with %r\n'
                    'Text content of paginators was: %r' % (page_text,
                    [elem.text for elem in b.find_elements_by_class_name('pagination')]))

    def click_page_number(self, page_text):
        b = self.browser
        b.find_element_by_xpath(u'//div[@class="pagination'
            ' pagination-right"]/ul/li/a[text()="%s"]' % page_text).click()
        # let the grid finish loading
        b.find_element_by_xpath('//table[contains(@class, "backgrid")]'
                '/tbody[not(.//div[@class="loading-overlay"])]')

    def go_to_activity_grid(self):
        b = self.browser
        b.get(get_server_base() + 'activity/labcontroller?page_size=%d' % self.page_size)
        b.find_element_by_class_name('search-query').send_keys(
                'lab_controller.fqdn:%s' % self.lc.fqdn)
        b.find_element_by_class_name('grid-filter').submit()
        # let the grid finish loading
        b.find_element_by_xpath('//table[contains(@class, "backgrid")]'
                '/tbody[not(.//div[@class="loading-overlay"])]')

    def test_single_page(self):
        self.create_activity_pages(1)
        self.go_to_activity_grid()
        self.check_page_text_is_shown('1', current=True)

    def test_pagination_links_exist_with_five_pages(self):
        self.create_activity_pages(5)
        self.go_to_activity_grid()
        for number in range(1,6):
            self.check_page_text_is_shown(number, True if number is 1 else False)

    def test_no_ellipsis_with_six_pages(self):
        # We're expecting 1 2 3 4 5 6 and no ellipsis.
        b = self.browser
        self.create_activity_pages(6)
        self.go_to_activity_grid()
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
        self.go_to_activity_grid()
        # We will be on page 1...
        self.check_page_text_is_shown(u'…8')

        self.click_page_number('4')
        self.check_page_text_is_shown(u'…8')
        self.check_page_text_is_shown('1')

        self.click_page_number('5')
        self.check_page_text_is_shown(u'1…')
        self.check_page_text_is_shown('8')
