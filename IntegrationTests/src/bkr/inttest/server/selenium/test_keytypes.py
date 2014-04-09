
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest import get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login

class KeyTypesTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1012404
    def test_add_key_type(self):
        new_key_name = u'AARDVARK'
        b = self.browser
        login(b)
        b.get(get_server_base() + 'keytypes/')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//h1[text()="New Key Type"]')
        b.find_element_by_name('key_name').send_keys(new_key_name)
        b.find_element_by_id('keytypes').submit()
        b.find_element_by_xpath('//table/tbody/tr/td[1]'
                '[normalize-space(string(.))="%s"]' % new_key_name)
