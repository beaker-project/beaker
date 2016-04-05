
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, is_text_present, \
        delete_and_confirm
from bkr.inttest import data_setup, get_server_base
import unittest, time, re, os
from turbogears.database import session
import crypt

class UserPrefs(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.user = data_setup.create_user(password='password')
        login(self.browser, user=self.user.user_name, password='password')

        self.clear_password = 'gyfrinachol'
        self.hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'
        self.simple_password = 's3cr3t'

    def go_to_prefs_tab(self, tab):
        b = self.browser
        b.get(get_server_base() + 'prefs/')
        tab_link = b.find_element_by_xpath(
                '//ul[contains(@class, "nav-tabs")]//a[text()="%s"]' % tab)
        tab_link.click()
        # XXX is there a timing issue here? unsure
        return b.find_element_by_css_selector('.tab-pane.active')

    def test_adding_invalid_delegate(self):
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Submission Delegates')
        delegate_field = pane.find_element_by_name('user_name')
        # Add an invalid user
        delegate_field.send_keys('randuseriosgfsy89238')
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('Submission delegate randuseriosgfsy89238 does not exist',
                pane.find_element_by_class_name('alert-error').text)

    def test_adding_duplicate_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user()
            self.user.submission_delegates[:] = [submission_delegate]
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Submission Delegates')
        delegate_field = pane.find_element_by_name('user_name')
        # Add the submission delegate again
        delegate_field.send_keys(submission_delegate.user_name)
        pane.find_element_by_tag_name('form').submit()
        # Should do nothing, input should be cleared
        # (:invalid selector matches when the value is empty, because it's required)
        pane.find_element_by_css_selector('input[name=user_name]:invalid')
        # Check that it hasn't changed our list of submission delegates
        with session.begin():
            session.expire_all()
            self.assertEquals(self.user.submission_delegates, [submission_delegate])

    def test_removing_submission_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user()
            self.user.submission_delegates[:] = [submission_delegate]
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Submission Delegates')
        pane.find_element_by_xpath('//li[a/text()="%s"]'
                '/button[contains(text(), "Remove")]'
                % submission_delegate.user_name).click()
        b.find_element_by_xpath('//div[@id="submission-delegates" and not(.//ul/li)]')
        # Check they have been removed in DB
        session.expire(self.user)
        with session.begin():
            self.assertEquals(self.user.submission_delegates, [])
            activity = self.user.user_activity[-1]
            self.assertEqual(activity.action, u'Removed')
            self.assertEqual(activity.field_name, u'Submission delegate')
            self.assertEqual(activity.user.user_id, self.user.user_id)
            self.assertEqual(activity.old_value, submission_delegate.user_name)
            self.assertEqual(activity.new_value, None)

    def test_adding_submission_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user()
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Submission Delegates')
        delegate_field = pane.find_element_by_name('user_name')
        delegate_field.send_keys(submission_delegate.user_name)
        pane.find_element_by_tag_name('form').submit()
        pane.find_element_by_xpath('//ul/li[a/text()="%s"]'
                % submission_delegate.user_name)
        # Check user has indeed been added, and activity updated
        with session.begin():
            session.expire_all()
            self.assertEqual(self.user.submission_delegates, [submission_delegate])
            activity = self.user.user_activity[-1]
            self.assertEqual(activity.action, u'Added')
            self.assertEqual(activity.field_name,
                u'Submission delegate')
            self.assertEqual(activity.user_id, self.user.user_id)
            self.assertEqual(activity.new_value, submission_delegate.user_name)
            self.assertEqual(activity.old_value, None)

    def test_set_plaintext_password(self):
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Root Password')
        e = pane.find_element_by_name('root_password')
        e.send_keys(self.clear_password)
        pane.find_element_by_tag_name('form').submit()
        pane.find_element_by_xpath('p[contains(text(), "Your root password was set")'
                ' and normalize-space(string(time))="a few seconds ago"]')
        new_hash = pane.find_element_by_xpath('p[1]/code').text
        self.failUnless(new_hash)
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == new_hash)

    def test_set_hashed_password(self):
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Root Password')
        e = pane.find_element_by_name('root_password')
        e.send_keys(self.hashed_password)
        pane.find_element_by_tag_name('form').submit()
        pane.find_element_by_xpath('p[contains(text(), "Your root password was set")'
                ' and normalize-space(string(time))="a few seconds ago"]')
        new_hash = pane.find_element_by_xpath('p[1]/code').text
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == self.hashed_password)

    def test_dictionary_password_rejected(self):
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Root Password')
        e = pane.find_element_by_name('root_password')
        e.send_keys(self.simple_password)
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('Root password is based on a dictionary word',
                pane.find_element_by_class_name('alert-error').text)

    def test_ssh_key_allows_whitespace_in_description(self):
        b = self.browser
        key = 'ssh-rsa AAAAw00t this is my favourite key'
        pane = self.go_to_prefs_tab('SSH Public Keys')
        pane.find_element_by_name('key').send_keys(key)
        pane.find_element_by_tag_name('form').submit()
        pane.find_element_by_xpath(
                '//li/span[@class="ident" and text()="this is my favourite key"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_ssh_key_trailing_whitespace_is_stripped(self):
        b = self.browser
        key = 'ssh-rsa AAAAw00t me@example.com  \n\n'
        pane = self.go_to_prefs_tab('SSH Public Keys')
        pane.find_element_by_name('key').send_keys(key)
        pane.find_element_by_tag_name('form').submit()
        pane.find_element_by_xpath(
                '//li/span[@class="ident" and text()="me@example.com"]')
        with session.begin():
            self.assertEquals(self.user.sshpubkeys[-1].ident, 'me@example.com')

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_multiple_ssh_keys_not_accepted(self):
        b = self.browser
        key = 'ssh-rsa AAAAw00t me@example.com\nssh-rsa AAAAlol another key'
        pane = self.go_to_prefs_tab('SSH Public Keys')
        pane.find_element_by_name('key').send_keys(key)
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('SSH public keys may not contain newlines',
                pane.find_element_by_class_name('alert-error').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_invalid_ssh_key_not_accepted(self):
        b = self.browser
        pane = self.go_to_prefs_tab('SSH Public Keys')
        pane.find_element_by_name('key').send_keys('gibberish')
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('Invalid SSH public key',
                pane.find_element_by_class_name('alert-error').text)

    def test_set_use_old_job_page(self):
        with session.begin():
            self.user.use_old_job_page = True
        b = self.browser
        pane = self.go_to_prefs_tab('User Interface')
        checkbox = pane.find_element_by_name('use_old_job_page')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        pane.find_element_by_tag_name('form').submit()
        # When the button changes back to Save Changes it means it's finished saving
        save_btn = pane.find_element_by_xpath('//button[text()="Save Changes"]')
        self.assertFalse(save_btn.is_enabled())
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.use_old_job_page, False)
