
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase

from bkr.inttest.server.webdriver_utils import login


class TestHelp(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_help_is_available(self):
        b = self.browser
        login(b)
        b.find_element_by_link_text('Help').click()
        b.find_element_by_xpath("//ul[@id='help-menu']//a[text()='Documentation' \
                                and @href='http://beaker-project.org/docs/']")
        b.find_element_by_xpath("//ul[@id='help-menu']//a[text()='Report a Bug' \
                                and @href='https://github.com/beaker-project/beaker/issues/']")
