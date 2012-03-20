#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session
import crypt

class UserPrefs(SeleniumTestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.clear_password = 'gyfrinachol'
        self.hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'
        self.simple_password = 's3cr3t'

    def test_set_plaintext_password(self):
        sel = self.selenium
        sel.open("")
        self.login()
        sel.click("link=Preferences")
        sel.wait_for_page_to_load("30000")
        sel.type("UserPrefs_root_password", "%s" % self.clear_password)
        sel.click("//input[@value='Change']")
        sel.wait_for_page_to_load("30000")
        self.failUnless('root password hash changed' in sel.get_text('css=.flash'))
        new_hash = sel.get_value('//input[@id="UserPrefs_root_password"]')
        self.failUnless(new_hash)
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == new_hash)

    def test_set_hashed_password(self):
        sel = self.selenium
        sel.open("")
        self.login()
        sel.click("link=Preferences")
        sel.wait_for_page_to_load("30000")
        sel.type("UserPrefs_root_password", "%s" % self.hashed_password)
        sel.click("//input[@value='Change']")
        sel.wait_for_page_to_load("30000")
        self.failUnless('root password hash changed' in sel.get_text('css=.flash'))
        new_hash = sel.get_value('//input[@id="UserPrefs_root_password"]')
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == self.hashed_password)

    def test_dictionary_password_rejected(self):
        sel = self.selenium
        sel.open("")
        self.login()
        sel.click("link=Preferences")
        sel.wait_for_page_to_load("30000")
        sel.type("UserPrefs_root_password", "%s" % self.simple_password)
        sel.click("//input[@value='Change']")
        sel.wait_for_page_to_load("30000")
        self.failUnless('Root password not changed' in sel.get_text('css=.flash'))

    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
