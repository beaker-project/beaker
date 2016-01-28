
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
            self.user2 = data_setup.create_user()
        login(self.browser, user=self.user.user_name, password='password')
        self.browser.get(get_server_base() + 'prefs')

        self.clear_password = 'gyfrinachol'
        self.hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'
        self.simple_password = 's3cr3t'

    def test_adding_invalid_delegate(self):
        b = self.browser
        delegate_field = b.find_element_by_id('SubmissionDelegates_user_text')
        # Add an invalid user
        delegate_field.send_keys('randuseriosgfsy89238')
        b.find_element_by_id('SubmissionDelegates').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            'randuseriosgfsy89238 is not a valid user')

    def test_adding_duplicate_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user()
            self.user.submission_delegates[:] = [submission_delegate]
        b = self.browser
        delegate_field = b.find_element_by_id('SubmissionDelegates_user_text')
        # Add the submission delegate again
        delegate_field.send_keys(submission_delegate.user_name)
        b.find_element_by_id('SubmissionDelegates').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            '%s is already a submission delegate for %s' % (submission_delegate, self.user))
        # Check that it hasn't changed our list of submission delegates
        self.assertEquals(self.user.submission_delegates, [submission_delegate])

    def test_removing_submission_delegate(self):
        with session.begin():
            submission_delegate = data_setup.create_user()
            self.user.submission_delegates[:] = [submission_delegate]
        b = self.browser
        b.get(get_server_base() + 'prefs')
        delete_and_confirm(b, '//td[preceding-sibling::td/text()="%s"]'
                % submission_delegate, 'Remove (-)')
        self.assertEquals(b.find_element_by_class_name('flash').text,
            '%s removed as a submission delegate' % submission_delegate)
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
        delegate_field = b.find_element_by_id('SubmissionDelegates_user_text')
        delegate_field.send_keys(submission_delegate.user_name)
        b.find_element_by_id('SubmissionDelegates').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            'Added %s as a submission delegate' % submission_delegate)
        session.expire(self.user)
        # Check user has indeed been added, and activity updated
        with session.begin():
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
        error_msg = b.find_element_by_css_selector(
                '#ssh_key_add .control-group.error .help-inline').text
        self.assertEquals(error_msg, 'SSH public keys may not contain newlines')

    # https://bugzilla.redhat.com/show_bug.cgi?id=830475
    def test_invalid_ssh_key_not_accepted(self):
        b = self.browser
        b.find_element_by_name('ssh_pub_key').send_keys('gibberish')
        b.find_element_by_id('ssh_key_add').submit()
        error_msg = b.find_element_by_css_selector(
                '#ssh_key_add .control-group.error .help-inline').text
        self.assert_('not a valid SSH public key' in error_msg)
