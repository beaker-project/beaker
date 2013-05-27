#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, is_text_present
from bkr.inttest import data_setup, get_server_base
import unittest, time, re, os
from turbogears.database import session
import crypt

class UserPrefs(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.user = data_setup.create_user(password='password')
            self.user2 = data_setup.create_user()
        login(self.browser, user=self.user.user_name, password='password')
        self.browser.get(get_server_base() + 'prefs')

        self.clear_password = 'gyfrinachol'
        self.hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'
        self.simple_password = 's3cr3t'

    def tearDown(self):
        self.browser.quit()

    def test_modifying_beaker_password(self):
        b = self.browser
        pass_field = b.find_element_by_name("password")
        pass_field.clear()
        pass_field.send_keys('AlbiDoubleyou')
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'Beaker password changed'))

        # Test that we can login with new creds
        # If we can't make the prefs page, we are not logged in
        logout(b)
        login(b, user=self.user.user_name, password='AlbiDoubleyou')
        self.browser.get(get_server_base() + 'prefs')
        b.find_element_by_xpath('//h2[text()="Preferences"]')

    def test_modifying_email(self):
        current_user_email = self.user.email_address
        b = self.browser

        # Try and use the same email as an existing user
        e = b.find_element_by_name("email_address")
        e.clear()
        e.send_keys(self.user2.email_address)
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'Email address is not unique'))

        # Check invalid email
        self.browser.get(get_server_base() + 'prefs')
        e = b.find_element_by_name("email_address")
        e.clear()
        e.send_keys('InvalidEmailAddress')
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'An email address must contain a single @'))

        # Check new unused  and valid email
        self.browser.get(get_server_base() + 'prefs')
        e = b.find_element_by_name("email_address")
        e.clear()
        e.send_keys('%s@domain.com' % data_setup.unique_name('dude%s'))
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'Email address changed'))

    def test_set_plaintext_password(self):
        b = self.browser
        e = b.find_element_by_name("_root_password")
        e.clear()
        e.send_keys(self.clear_password)
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'root password hash changed'))
        new_hash = b.find_element_by_name('_root_password').get_attribute('value')
        self.failUnless(new_hash)
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == new_hash)

    def test_set_hashed_password(self):
        b = self.browser
        e = b.find_element_by_name("_root_password")
        e.clear()
        e.send_keys(self.hashed_password)
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'root password hash changed'))
        new_hash = b.find_element_by_name('_root_password').get_attribute('value')
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == self.hashed_password)

    def test_dictionary_password_rejected(self):
        b = self.browser
        e = b.find_element_by_name("_root_password")
        e.clear()
        e.send_keys(self.simple_password)
        b.find_element_by_id('UserPrefs').submit()
        self.assert_(is_text_present(b, 'Root password not changed'))

    def test_ssh_key_allows_whitespace_in_description(self):
        b = self.browser
        key = 'ssh-rsa AAAAw00t this is my favourite key'
        b.find_element_by_name('ssh_pub_key').send_keys(key)
        b.find_element_by_id('ssh_key_add').submit()
        self.assert_(is_text_present(b, 'SSH public key added'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_ssh_key_trailing_whitespace_is_stripped(self):
        b = self.browser
        key = 'ssh-rsa AAAAw00t me@example.com  \n\n'
        b.find_element_by_name('ssh_pub_key').send_keys(key)
        b.find_element_by_id('ssh_key_add').submit()
        self.assert_(is_text_present(b, 'SSH public key added'))
        with session.begin():
            self.assertEquals(self.user.sshpubkeys[-1].ident, 'me@example.com')

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_multiple_ssh_keys_not_accepted(self):
        b = self.browser
        key = 'ssh-rsa AAAAw00t me@example.com\nssh-rsa AAAAlol another key'
        b.find_element_by_name('ssh_pub_key').send_keys(key)
        b.find_element_by_id('ssh_key_add').submit()
        error_msg = b.find_element_by_xpath(
                '//form[@id="ssh_key_add"]//td[textarea[@name="ssh_pub_key"]]'
                '/span[@class="fielderror"]').text
        self.assertEquals(error_msg, 'SSH public keys may not contain newlines')

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_invalid_ssh_key_not_accepted(self):
        b = self.browser
        b.find_element_by_name('ssh_pub_key').send_keys('gibberish')
        b.find_element_by_id('ssh_key_add').submit()
        error_msg = b.find_element_by_xpath(
                '//form[@id="ssh_key_add"]//td[textarea[@name="ssh_pub_key"]]'
                '/span[@class="fielderror"]').text
        self.assert_('not a valid SSH public key' in error_msg)

if __name__ == "__main__":
    unittest.main()
