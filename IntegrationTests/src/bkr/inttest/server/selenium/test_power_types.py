
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.server.selenium import WebDriverTestCase
from selenium.common.exceptions import NoSuchElementException


class TestPowerTypesGrid(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215034
    def test_anonymous(self):
        b = self.browser
        b.get(get_server_base() + 'powertypes/')
        try:
            b.find_element_by_link_text('Add')
            self.fail('Must fail')
        except NoSuchElementException:
            pass
        try:
            b.find_element_by_link_text('Remove')
            self.fail('Must fail')
        except NoSuchElementException:
            pass
        b.get(get_server_base() + 'powertypes/save')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
        b.get(get_server_base() + 'powertypes/new')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
        b.get(get_server_base() + 'powertypes/edit')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
        b.get(get_server_base() + 'powertypes/remove')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
