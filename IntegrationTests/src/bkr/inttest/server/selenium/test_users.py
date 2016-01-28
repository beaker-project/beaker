
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from bkr.server.model import session, SystemPermission, TaskStatus, User
from bkr.inttest import data_setup, DatabaseTestCase, get_server_base
from bkr.inttest.server.requests_utils import login as requests_login, \
        patch_json, post_json

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
        self.assertIn('Invalid email address', response.text)

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
            reserved_system = data_setup.create_system(status=u'Manual')
            reserved_system.reserve_manually(service=u'testdata', user=user)
            reserved_system.custom_access_policy.add_rule(
                    SystemPermission.reserve, user=user)
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
                    u'<grant reserve to %s>' % user.user_name)
            # systems owned by the user should be transferred to the caller
            self.assertEqual(owned_system.owner.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_system.activity[0].field_name, u'Owner')
            self.assertEqual(owned_system.activity[0].action, u'Changed')
            self.assertEqual(owned_system.activity[0].old_value, user.user_name)
            self.assertEqual(owned_system.activity[0].new_value, data_setup.ADMIN_USER)
            # group membership/ownership should be removed
            self.assertNotIn(group, user.groups)
            self.assertNotIn(user, group.users)
            self.assertFalse(group.has_owner(user))
            self.assertEqual(group.activity[-1].field_name, u'User')
            self.assertEqual(group.activity[-1].action, u'Removed')
            self.assertEqual(group.activity[-1].old_value, user.user_name)

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
