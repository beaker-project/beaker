# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.assertions import assert_has_key_with_value
from bkr.server.model import Arch, System, OSMajor
from turbogears.database import session
import pkg_resources
import unittest
from tempfile import NamedTemporaryFile
import requests

class CSVRoundtripTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.browser = self.get_browser()

    def import_csv(self, contents):
        b = self.browser
        b.get(get_server_base() + 'csv/csv_import')
        csv_file = NamedTemporaryFile(prefix=self.__module__)
        csv_file.write(contents)
        csv_file.flush()
        b.find_element_by_name('csv_file').send_keys(csv_file.name)
        b.find_element_by_name('csv_file').submit()

    def get_csv(self, csv_type):
        b = self.browser
        b.get(get_server_base() + 'csv/')
        b.find_element_by_xpath('//input[@name="csv_type" and @value="%s"]' % csv_type).click()
        url = get_server_base() + ('csv/action_export?csv_type=%s' % csv_type)
        cookies = dict((cookie['name'].encode('ascii', 'replace'), cookie['value'])
                for cookie in b.get_cookies())
        request = requests.get(url, cookies=cookies, stream=True)
        request.raise_for_status()
        return request.iter_lines()

    def test_system_export_reimport(self):
        login(self.browser)
        orig_date_modified = self.system.date_modified
        self.import_csv('\n'.join([row for row in self.get_csv('system')]))
        self.assertEquals(self.browser.find_element_by_xpath(
            '//table[@id="csv-import-log"]//td').text,
                          "No Errors")
        session.refresh(self.system)
        self.assert_(orig_date_modified != self.system.date_modified)
