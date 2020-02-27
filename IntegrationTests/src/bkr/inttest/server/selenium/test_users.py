# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from unittest import SkipTest
import requests
from bkr.server.model import session, SystemPermission, TaskStatus, User, SSHPubKey, SystemStatus
from bkr.inttest import data_setup, DatabaseTestCase, get_server_base
from bkr.inttest.server.requests_utils import (login as requests_login, patch_json,
                                               post_json, put_json, xmlrpc as requests_xmlrpc)
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, check_user_search_results
from turbogears import config


class UsersGridTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_search_by_username(self):
        with session.begin():
            user = data_setup.create_user()
            other_user = data_setup.create_user(user_name=u'aaardvark123')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/')
        b.find_element_by_class_name('search-query').send_keys(user.user_name)
        b.find_element_by_class_name('grid-filter').submit()
        check_user_search_results(b, present=[user], absent=[other_user])

    def test_add_duplicate_user(self):
        with session.begin():
            existing_user = data_setup.create_user(user_name=u'existing')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').send_keys(existing_user.user_name)
        modal.find_element_by_name('display_name').send_keys('anything')
        modal.find_element_by_name('email_address').send_keys(
            'anything@example.invalid')
        modal.find_element_by_tag_name('form').submit()
        self.assertIn('User %s already exists' % existing_user.user_name,
                      modal.find_element_by_class_name('alert-error').text)

    def test_adduser(self):
        user_1_name = data_setup.unique_name('anonymous%s')
        user_1_email = data_setup.unique_name('anonymous%s@my.com')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').send_keys(user_1_name)
        modal.find_element_by_name('display_name').send_keys(user_1_name)
        modal.find_element_by_name('email_address').send_keys(user_1_email)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//title[text()="%s"]' % user_1_name)


class UserTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'theuser')
        self.browser = self.get_browser()

    def test_unprivileged_view(self):
        # A regular unprivileged user will have access to see the info on
        # another user's page, but not to change anything.
        with session.begin():
            unprivileged = data_setup.create_user(password=u'unprivileged')
        b = self.browser
        login(b, user=unprivileged.user_name, password='unprivileged')
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1[contains(string(.), "%s")]' % self.user.user_name)
        b.find_element_by_xpath('//li[normalize-space(string(.))="Member of 0 groups"]')
        # no buttons or forms
        b.find_element_by_xpath('//body[not(.//form) and not(.//button)]')

    def test_user_can_reset_their_own_password(self):
        b = self.browser
        login(b, user=self.user.user_name, password='theuser')
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        password_form = b.find_element_by_xpath('//div[@class="password-reset"]//form')
        password_form.find_element_by_name('password').send_keys('newpass')
        password_form.submit()
        b.find_element_by_xpath('//h4[text()="Password has been reset"]')
        with session.begin():
            session.expire_all()
            self.assertTrue(self.user.check_password(u'newpass'))

    def test_user_can_edit_their_own_details(self):
        b = self.browser
        login(b, user=self.user.user_name, password='theuser')
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('display_name').clear()
        modal.find_element_by_name('display_name').send_keys('Bernie Sanders')
        modal.find_element_by_name('email_address').clear()
        modal.find_element_by_name('email_address').send_keys('bernie@whitehouse.gov')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath('//h1/small[normalize-space(string(.))='
                                '"Bernie Sanders <bernie@whitehouse.gov>"]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.user.display_name, u'Bernie Sanders')
            self.assertEqual(self.user.email_address, u'bernie@whitehouse.gov')

    def test_rename_user(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').clear()
        modal.find_element_by_name('user_name').send_keys(u'hclinton')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath('//title[text()="hclinton"]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.user.user_name, u'hclinton')

    def test_renaming_user_to_existing_username(self):
        with session.begin():
            other_user = data_setup.create_user()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').clear()
        modal.find_element_by_name('user_name').send_keys(other_user.user_name)
        modal.find_element_by_tag_name('form').submit()
        self.assertIn('User %s already exists' % other_user.user_name,
                      modal.find_element_by_class_name('alert-error').text)

    def test_disable_enable(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//button[contains(text(), "Disable")]').click()
        b.find_element_by_xpath('//div[@class="alert" and text()="Account is currently disabled."]')
        with session.begin():
            session.expire_all()
            self.assertTrue(self.user.disabled)
        b.find_element_by_xpath('//button[contains(text(), "Enable")]').click()
        # Wait for the button to change back to "Disable"
        b.find_element_by_xpath('//button[contains(text(), "Disable")]')
        with session.begin():
            session.expire_all()
            self.assertFalse(self.user.disabled)

    def test_delete_undelete(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//button[contains(text(), "Delete")]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[@class="alert" and contains(text(), "Account was removed")]')
        with session.begin():
            session.expire_all()
            # Behaviour of user removal is exhaustively covered below in HTTP tests.
            self.assertIsNotNone(self.user.removed)
        b.find_element_by_xpath('//button[contains(text(), "Undelete")]').click()
        # Wait for the button to change back to "Delete"
        b.find_element_by_xpath('//button[contains(text(), "Delete")]')
        with session.begin():
            session.expire_all()
            self.assertIsNone(self.user.removed)


class UserHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for users.
    """

    def test_get_user(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = s.get(get_server_base() + 'users/%s' % user.user_name,
                         headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['user_name'], user.user_name)

    def test_get_self(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = s.get(get_server_base() + 'users/+self',
                         headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['user_name'], user.user_name)
        self.assertEqual(response.json()['email_address'], user.email_address)

    def test_get_self_for_proxied_user(self):
        with session.begin():
            group = data_setup.create_group(permissions=[u'proxy_auth'])
            proxying_user = data_setup.create_user(password=u'password')
            group.add_member(proxying_user)
            proxied_user = data_setup.create_user()
        s = requests.Session()
        response = requests_xmlrpc(get_server_base() + 'RPC2',
                                   'auth.login_password',
                                   [proxying_user.user_name, u'password', proxied_user.user_name],
                                   session=s)
        response.raise_for_status()
        response = s.get(get_server_base() + 'users/+self',
                         headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['user_name'], proxied_user.user_name)
        self.assertEqual(response.json()['email_address'], proxied_user.email_address)
        self.assertEqual(response.json()['proxied_by_user']['user_name'],
                         proxying_user.user_name)

    def test_create_user(self):
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': 'fbaggins',
            'display_name': 'Frodo Baggins',
            'email_address': 'frodo@theshire.co.nz'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            user = User.by_user_name(u'fbaggins')
            self.assertEqual(response.json()['id'], user.user_id)
            self.assertEqual(response.json()['user_name'], 'fbaggins')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_user_with_empty_display_name(self):
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': 'fbagginsone',
            'display_name': '',
            'email_address': 'rodo@theshire.co.nz'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                         'Display name must not be empty')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_user_with_empty_email_address(self):
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': 'fbagginsone',
            'display_name': 'Frodo Baggins pne',
            'email_address': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email address must not be empty', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=997830
    def test_whitespace_only_values_are_not_accepted(self):
        # Whitespace-only values also count as empty, because we strip
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': ' \t\v',
            'display_name': 'Bilbo Baggins',
            'email_address': 'bilbo@theshire.co.nz'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, 'Username must not be empty')
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': 'bbaggins',
            'display_name': ' \t\v',
            'email_address': 'bilbo@theshire.co.nz'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, 'Display name must not be empty')
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': 'bbaggins',
            'display_name': 'Bilbo Baggins',
            'email_address': ' \t\v'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                         'Email address must not be empty')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1086505
    def test_non_ascii_username_and_display_name(self):
        user_name = u'ломоносов'
        display_name = u'Михаил Ломоносов'
        email = 'lomonosov@example.ru'
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'users/', session=s, data={
            'user_name': user_name,
            'display_name': display_name,
            'email_address': email})
        response.raise_for_status()

        # Test that search works as well
        response = s.get(get_server_base() + 'users/',
                         params={'q': u'user_name:%s' % user_name},
                         headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['entries'][0]['user_name'], user_name)

        # Test that typeahead works as well
        response = s.get(get_server_base() + 'users/+typeahead',
                         params={'q': user_name[:4]},
                         headers={'Accept': 'application/json'})
        self.assertEqual(response.json()['data'][0]['user_name'], user_name)

    def test_rename_user(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              session=s, data={'user_name': 'sgamgee'})
        response.raise_for_status()
        self.assertEqual(response.headers['Location'], get_server_base() + 'users/sgamgee')
        self.assertEqual(response.json()['user_name'], 'sgamgee')
        with session.begin():
            session.expire_all()
            self.assertEqual(user.user_name, u'sgamgee')

    def test_renaming_user_to_existing_username_gives_409(self):
        with session.begin():
            user = data_setup.create_user()
            other_user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              session=s, data={'user_name': other_user.user_name})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.text,
                         'User %s already exists' % other_user.user_name)

    def test_regular_users_cannot_rename_themselves(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              session=s, data={'user_name': 'gandalf'})
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot rename user', response.text)

    def test_update_display_name(self):
        with session.begin():
            user = data_setup.create_user(display_name=u'Frodo Baggins')
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'display_name': u'Frodo Gamgee'}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(user.display_name, u'Frodo Gamgee')

    def test_update_email_address(self):
        with session.begin():
            user = data_setup.create_user(email_address=u'frodo@theshire.co.nz')
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'email_address': u'frodo@mordor.com'}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(user.email_address, u'frodo@mordor.com')

    def test_invalid_email_address(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)

        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'email_address': u'asdf'}, session=s)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid email address', response.text)

        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'email_address': u''}, session=s)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email address must not be empty', response.text)

    def test_set_password(self):
        with session.begin():
            user = data_setup.create_user()
            user.password = u'frodo'
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'password': u'bilbo'}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(user.check_password(u'bilbo'))

    def test_set_root_password(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'root_password': u'D6BeK7Cq9a4M'}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIsNotNone(user._root_password)

    def test_clear_root_password(self):
        with session.begin():
            user = data_setup.create_user()
            user.root_password = u'D6BeK7Cq9a4M'
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'root_password': u''}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIsNone(user._root_password)

    def test_set_use_old_job_page(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            user.use_old_job_page = True
        s = requests.Session()
        requests_login(s, user=user.user_name, password='password')
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'use_old_job_page': False}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(user.use_old_job_page, False)

    def test_add_ssh_public_key(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = s.post(get_server_base() + 'users/%s/ssh-public-keys/' % user.user_name,
                          headers={'Content-Type': 'text/plain'},
                          data='ssh-rsa abc dummypassword@example.invalid')
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(user.sshpubkeys), 1)
            self.assertEqual(user.sshpubkeys[0].keytype, u'ssh-rsa')
            self.assertEqual(user.sshpubkeys[0].pubkey, u'abc')
            self.assertEqual(user.sshpubkeys[0].ident, u'dummypassword@example.invalid')

    def test_delete_ssh_public_key(self):
        with session.begin():
            user = data_setup.create_user()
            user.sshpubkeys.append(SSHPubKey(keytype=u'ssh-rsa',
                                             pubkey=u'abc', ident=u'asdf@example.invalid'))
        s = requests.Session()
        requests_login(s)
        response = s.delete(get_server_base() + 'users/%s/ssh-public-keys/%s'
                            % (user.user_name, user.sshpubkeys[0].id))
        self.assertEqual(response.status_code, 204)
        with session.begin():
            session.expire_all()
            self.assertEqual(len(user.sshpubkeys), 0)

    def test_add_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user()
            other_user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'users/%s/submission-delegates/' % user.user_name,
                             session=s, data={'user_name': other_user.user_name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertItemsEqual(user.submission_delegates, [other_user])

    def test_remove_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user()
            other_user = data_setup.create_user()
            user.add_submission_delegate(other_user, service=u'testdata')
        s = requests.Session()
        requests_login(s)
        response = s.delete(get_server_base() + 'users/%s/submission-delegates/' % user.user_name,
                            params={'user_name': other_user.user_name})
        self.assertEqual(response.status_code, 204)
        with session.begin():
            session.expire_all()
            self.assertEqual(len(user.submission_delegates), 0)

    def test_disable_user(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'disabled': True}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(user.disabled)

    def test_reenable_user(self):
        with session.begin():
            user = data_setup.create_user()
            user.disabled = True
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'disabled': False}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertFalse(user.disabled)

    def test_remove_account(self):
        with session.begin():
            user = data_setup.create_user()
            job = data_setup.create_job(owner=user)
            data_setup.mark_job_running(job)
            owned_system = data_setup.create_system(owner=user)
            loaned_system = data_setup.create_system()
            loaned_system.loaned = user
            reserved_system = data_setup.create_system(status=SystemStatus.manual)
            reserved_system.reserve_manually(service=u'testdata', user=user)
            reserved_system.custom_access_policy.add_rule(
                SystemPermission.reserve, user=user)
            owned_pool = data_setup.create_system_pool(owning_user=user)
            group = data_setup.create_group(owner=user)
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'removed': 'now'}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIsNotNone(user.removed)
            # running jobs should be cancelled
            job.update_status()
            self.assertEquals(job.status, TaskStatus.cancelled)
            self.assertIn('User %s removed' % user.user_name,
                          job.recipesets[0].recipes[0].tasks[0].results[0].log)
            # reservations should be released
            self.assertIsNone(reserved_system.user)
            # loans should be returned
            self.assertIsNone(loaned_system.loaned)
            # access policy rules should be removed
            self.assertEqual([],
                             [rule for rule in reserved_system.custom_access_policy.rules
                              if rule.user == user])
            self.assertEqual(reserved_system.activity[0].field_name, u'Access Policy Rule')
            self.assertEqual(reserved_system.activity[0].action, u'Removed')
            self.assertEqual(reserved_system.activity[0].old_value,
                             u'User:%s:reserve' % user.user_name)
            # systems owned by the user should be transferred to the caller
            self.assertEqual(owned_system.owner.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_system.activity[0].field_name, u'Owner')
            self.assertEqual(owned_system.activity[0].action, u'Changed')
            self.assertEqual(owned_system.activity[0].old_value, user.user_name)
            self.assertEqual(owned_system.activity[0].new_value, data_setup.ADMIN_USER)
            # pools owned by the user should be transferred to the caller
            self.assertEqual(owned_pool.owner.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_pool.activity[0].field_name, u'Owner')
            self.assertEqual(owned_pool.activity[0].action, u'Changed')
            self.assertEqual(owned_pool.activity[0].old_value, user.user_name)
            self.assertEqual(owned_pool.activity[0].new_value, data_setup.ADMIN_USER)
            # group membership/ownership should be removed
            self.assertNotIn(group, user.groups)
            self.assertNotIn(user, group.users)
            self.assertFalse(group.has_owner(user))
            self.assertEqual(group.activity[-1].field_name, u'User')
            self.assertEqual(group.activity[-1].action, u'Removed')
            self.assertEqual(group.activity[-1].old_value, user.user_name)

    def test_user_resource_counts_are_accurate_when_removing(self):
        with session.begin():
            user = data_setup.create_user()
            job = data_setup.create_job(owner=user)
            data_setup.mark_job_running(job)
            owned_system = data_setup.create_system(owner=user)
            loaned_system = data_setup.create_system()
            loaned_system.loaned = user
            owned_pool = data_setup.create_system_pool(owning_user=user)
            group = data_setup.create_group(owner=user)
        s = requests.Session()
        requests_login(s)
        response = s.get(get_server_base() + 'users/%s' % user.user_name,
                         headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEquals(response.json()['job_count'], 1)
        self.assertEquals(response.json()['reservation_count'], 1)
        self.assertEquals(response.json()['loan_count'], 1)
        self.assertEquals(response.json()['owned_system_count'], 1)
        self.assertEquals(response.json()['owned_pool_count'], 1)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'removed': 'now'}, session=s)
        response.raise_for_status()
        # The bug was that the counts in the PATCH response would still show
        # their old values, because the queries for producing the counts were
        # being run before all the removals were flushed to the database.
        # Note that job_count stays as 1, because the job has been cancelled
        # but it will still be running until the next iteration of beakerd's
        # update_dirty_jobs.
        self.assertEquals(response.json()['job_count'], 1)
        self.assertEquals(response.json()['reservation_count'], 0)
        self.assertEquals(response.json()['loan_count'], 0)
        self.assertEquals(response.json()['owned_system_count'], 0)
        self.assertEquals(response.json()['owned_pool_count'], 0)

    def test_unremove_account(self):
        with session.begin():
            user = data_setup.create_user()
            user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() + 'users/%s' % user.user_name,
                              data={'removed': None}, session=s)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIsNone(user.removed)
            self.assertFalse(user.disabled)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1100519
    def test_cannot_create_keystone_trust_if_openstack_is_disabled(self):
        if config.get('openstack.identity_api_url'):
            raise SkipTest('OpenStack integration is enabled')
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s)
        response = put_json(get_server_base() + 'users/%s/keystone-trust' % user.user_name,
                            session=s, data={'openstack_username': u'dummyuser'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('OpenStack Integration is not enabled', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1557847
    def test_can_delete_keystone_trust_if_openstack_session_is_invalid(self):
        # Create a user with an invalid trust id. The bug was caused during the
        # construction of the DynamicVirt instance, which failed due to an
        # authentication problem. The user can always update their credentials,
        # so expect in case Beaker can not create a keystone session that the
        # trust has been deleted or invalidated somehow by other means.
        user_password = 'givemeoneopenstack'
        with session.begin():
            user = data_setup.create_user(password=user_password)
            user.openstack_trust_id = 'openstackisgreatwhenyoudonthavetouseit'
        sess = requests.Session()
        requests_login(sess, user, user_password)
        response = sess.delete(
            get_server_base() + 'users/%s/keystone-trust' % user.user_name)
        self.assertEqual('', response.text)
        self.assertEqual(response.status_code, 204)
        with session.begin():
            session.expire_all()
            self.assertIsNone(user.openstack_trust_id)
