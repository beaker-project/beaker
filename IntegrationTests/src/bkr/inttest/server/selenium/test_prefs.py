# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import SSHPubKey
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from unittest import SkipTest
from turbogears.database import session
from turbogears import config
import crypt


class UserPrefs(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.user = data_setup.create_user(password='password')
        login(self.browser, user=self.user.user_name, password='password')

        self.clear_password = 'gyfrinachol'
        self.hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'

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

    def test_too_short_password_is_rejected(self):
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Root Password')
        e = pane.find_element_by_name('root_password')
        e.send_keys('s3cr3t')
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('The root password is shorter than 7 characters',
                      pane.find_element_by_class_name('alert-error').text)

    def test_dictionary_password_rejected(self):
        b = self.browser
        pane = self.go_to_prefs_tab(tab='Root Password')
        e = pane.find_element_by_name('root_password')
        e.send_keys('s3cr3tive')
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('The root password fails the dictionary check - '
                      'it is based on a dictionary word',
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1175584
    def test_duplicate_ssh_key_not_accepted(self):
        sshkey = (u'ssh-rsa', u'uniquekey', u'domain@example.com')
        with session.begin():
            self.user.sshpubkeys.append(SSHPubKey(*sshkey))
        key = 'ssh-rsa %s different_domain@xample.com' % sshkey[1]
        pane = self.go_to_prefs_tab('SSH Public Keys')
        pane.find_element_by_name('key').send_keys(key)
        pane.find_element_by_tag_name('form').submit()
        self.assertIn('Duplicate SSH public key',
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
        pane.find_element_by_xpath('.//button[normalize-space(string(.))'
                                   '="Save Changes" and @disabled=""]')
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.use_old_job_page, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_set_job_completion_notify_off(self):
        with session.begin():
            self.user.notify_job_completion = True
        b = self.browser
        pane = self.go_to_prefs_tab('Notifications')
        checkbox = pane.find_element_by_name('notify_job_completion')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        pane.find_element_by_tag_name('form').submit()
        # When the button changes back to Save Changes it means it's finished saving
        pane.find_element_by_xpath('.//button[normalize-space(string(.))'
                                   '="Save Changes" and @disabled=""]')
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.notify_job_completion, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_set_broken_system_notify_off(self):
        with session.begin():
            self.user.notify_broken_system = True
        b = self.browser
        pane = self.go_to_prefs_tab('Notifications')
        checkbox = pane.find_element_by_name('notify_broken_system')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        pane.find_element_by_tag_name('form').submit()
        # When the button changes back to Save Changes it means it's finished saving
        pane.find_element_by_xpath('.//button[normalize-space(string(.))'
                                   '="Save Changes" and @disabled=""]')
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.notify_broken_system, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=996165
    def test_set_system_loan_notify_off(self):
        with session.begin():
            self.user.notify_system_loan = True
        b = self.browser
        pane = self.go_to_prefs_tab('Notifications')
        checkbox = pane.find_element_by_name('notify_system_loan')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        pane.find_element_by_tag_name('form').submit()
        # When the button changes back to Save Changes it means it's finished saving
        pane.find_element_by_xpath('.//button[normalize-space(string(.))'
                                   '="Save Changes" and @disabled=""]')
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.notify_system_loan, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_set_group_modify_notify_off(self):
        with session.begin():
            self.user.notify_group_membership = True
        b = self.browser
        pane = self.go_to_prefs_tab('Notifications')
        checkbox = pane.find_element_by_name('notify_group_membership')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        pane.find_element_by_tag_name('form').submit()
        # When the button changes back to Save Changes it means it's finished saving
        pane.find_element_by_xpath('.//button[normalize-space(string(.))'
                                   '="Save Changes" and @disabled=""]')
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.notify_group_membership, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_set_system_reserved_notify_off(self):
        with session.begin():
            self.user.notify_reservesys = True
        b = self.browser
        pane = self.go_to_prefs_tab('Notifications')
        checkbox = pane.find_element_by_name('notify_reservesys')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        pane.find_element_by_tag_name('form').submit()
        # When the button changes back to Save Changes it means it's finished saving
        pane.find_element_by_xpath('.//button[normalize-space(string(.))'
                                   '="Save Changes" and @disabled=""]')
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.notify_reservesys, False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_revert_notification_preferences(self):
        with session.begin():
            self.user.notify_job_completion = True
            self.user.notify_broken_system = True
            self.user.notify_group_membership = False
            self.user.notify_reservesys = False
        b = self.browser
        pane = self.go_to_prefs_tab('Notifications')
        checkbox_notify_job = pane.find_element_by_name('notify_job_completion')
        self.assertTrue(checkbox_notify_job.is_selected())
        checkbox_notify_job.click()
        revert_btn = pane.find_element_by_xpath('.//button[normalize-space'
                                                '(string(.))="Revert"]')
        revert_btn.click()
        with session.begin():
            session.refresh(self.user)
            self.assertEqual(self.user.notify_job_completion, True)
            self.assertEqual(self.user.notify_broken_system, True)
            self.assertEqual(self.user.notify_group_membership, False)
            self.assertEqual(self.user.notify_reservesys, False)

    def test_virt_set_keystone_trusts_invalid(self):
        if not config.get('openstack.identity_api_url'):
            raise SkipTest('OpenStack Integration is not enabled')
        b = self.browser
        pane = self.go_to_prefs_tab('OpenStack Keystone Trust')
        pane.find_element_by_name('openstack_username').send_keys('invalid')
        pane.find_element_by_name('openstack_password').send_keys('invalid')
        pane.find_element_by_name('openstack_project_name').send_keys('invalid')
        pane.find_element_by_tag_name('form').submit()
        self.assertIn(
            'Could not authenticate with OpenStack using your credentials: The request you have made requires authentication.',
            pane.find_element_by_class_name('alert-error').text)
