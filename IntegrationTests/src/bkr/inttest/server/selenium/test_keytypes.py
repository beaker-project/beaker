
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from selenium.common.exceptions import NoSuchElementException
from bkr.server.model import Key
from bkr.inttest import get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.server.tests import data_setup
from bkr.server.model import Key


class KeyTypesTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=970921
    def test_add_numeric_key_type(self):
        new_key_name = data_setup.unique_name(u'FROB%s')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'keytypes/')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//h1[text()="New Key Type"]')
        b.find_element_by_name('key_name').send_keys(new_key_name)
        b.find_element_by_name('numeric').click()
        b.find_element_by_id('keytypes').submit()
        b.find_element_by_link_text('F').click()
        b.find_element_by_xpath('//table/tbody/tr/td[1]'
                '[normalize-space(string(.))="%s"]' % new_key_name)

        with session.begin():
            keytype = Key.query.filter_by(key_name=new_key_name).first()
            self.assertEqual(keytype.numeric, True)

    # https://bugzilla.redhat.com/show_bug.cgi?id=647563
    def test_uncheck_numeric_keytype(self):
        with session.begin():
            key = Key(data_setup.unique_name(u'FOOBAR%s'), numeric=1)
            session.add(key)

        b = self.browser
        login(b)
        b.get(get_server_base() + 'keytypes/')
        b.find_element_by_link_text('F').click()
        b.find_element_by_link_text(key.key_name).click()
        b.find_element_by_name('numeric').click()
        b.find_element_by_id('keytypes').submit()

        with session.begin():
            session.refresh(key)
            self.assertEqual(key.numeric, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=979270
    def test_no_error_with_duplicate_key_type(self):
        with session.begin():
            key = Key.query.first()

        b = self.browser
        login(b)
        b.get(get_server_base() + 'keytypes/')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('key_name').send_keys(key.key_name)
        b.find_element_by_id('keytypes').submit()
        self.assertEqual('Key Type exists: %s' % key.key_name,
                         b.find_element_by_xpath('//div[contains(@class, "alert flash")]').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215034
    def test_anonymous(self):
        b = self.browser
        b.get(get_server_base() + 'keytypes/')
        b.find_element_by_xpath('//div[@class="container-fluid"]//table[@id="widget"][not(tbody/tr/td/a)]')
        b.find_element_by_xpath('//div[@class="container-fluid" and not(//a[text()="Add"])]')
        b.get(get_server_base() + 'keytypes/save')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
        b.get(get_server_base() + 'keytypes/new')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
        b.get(get_server_base() + 'keytypes/edit')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
        b.get(get_server_base() + 'keytypes/remove')
        self.assertEquals(b.find_element_by_css_selector('#message').text,
                'Please log in.')
