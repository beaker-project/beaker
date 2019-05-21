# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase
from bkr.server.model import TaskStatus, User, SystemPermission, SystemStatus

class RemoveAccountTest(ClientTestCase):

    def test_admin_delete_self(self):
        try:
            run_client(['bkr', 'remove-account', 'admin'])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('You cannot remove yourself', e.stderr_output)

    def test_remove_multiple_users(self):
        with session.begin():
            user1 = data_setup.create_user(password=u'asdf')
            user2 = data_setup.create_user(password=u'qwerty')

        run_client(['bkr', 'remove-account', user1.user_name, user2.user_name])
        with session.begin():
            session.refresh(user1)
            session.refresh(user2)
            self.assertTrue(user1.removed)
            self.assertTrue(user2.removed)

    def test_remove_an_already_removed_user(self):
        with session.begin():
            user = data_setup.create_user()
        run_client(['bkr', 'remove-account', user.user_name])
        try:
            run_client(['bkr', 'remove-account', user.user_name])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('User already removed', e.stderr_output)

    def test_non_admin_cannot_delete(self):
        with session.begin():
            user3 = data_setup.create_user(password=u'qwerty')
            client_config1 = create_client_config(username = user3.user_name,
                                                  password='qwerty')
        try:
            # it's okay to use the same user since we won't reach there anyway :-)
            run_client(['bkr', 'remove-account', user3.user_name],
                       config=client_config1)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('Not member of group: admin', e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1257020
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
        run_client(['bkr', 'remove-account', user.user_name])
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
            self.assertEqual(reserved_system.activity[1].user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(reserved_system.activity[1].field_name, u'User')
            self.assertEqual(reserved_system.activity[1].action, u'Returned')
            self.assertEqual(reserved_system.activity[1].old_value, user.user_name)
            self.assertEqual(reserved_system.activity[1].new_value, u'')
            # loans should be returned
            self.assertIsNone(loaned_system.loaned)
            self.assertEqual(loaned_system.activity[0].user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(loaned_system.activity[0].field_name, u'Loaned To')
            self.assertEqual(loaned_system.activity[0].action, u'Changed')
            self.assertEqual(loaned_system.activity[0].old_value, user.user_name)
            self.assertEqual(loaned_system.activity[0].new_value, None)
            # access policy rules should be removed
            self.assertEqual([],
                    [rule for rule in reserved_system.custom_access_policy.rules
                     if rule.user == user])
            self.assertEqual(reserved_system.activity[0].user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(reserved_system.activity[0].field_name, u'Access Policy Rule')
            self.assertEqual(reserved_system.activity[0].action, u'Removed')
            self.assertEqual(reserved_system.activity[0].old_value,
                    u'User:%s:reserve' % user.user_name)
            self.assertEqual(reserved_system.activity[0].new_value, None)
            # systems owned by the user should be transferred to the caller
            self.assertEqual(owned_system.owner.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_system.activity[0].user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_system.activity[0].field_name, u'Owner')
            self.assertEqual(owned_system.activity[0].action, u'Changed')
            self.assertEqual(owned_system.activity[0].old_value, user.user_name)
            self.assertEqual(owned_system.activity[0].new_value, data_setup.ADMIN_USER)
            # pools owned by the user should be transferred to the caller
            self.assertEqual(owned_pool.owner.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_pool.activity[0].user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(owned_pool.activity[0].field_name, u'Owner')
            self.assertEqual(owned_pool.activity[0].action, u'Changed')
            self.assertEqual(owned_pool.activity[0].old_value, user.user_name)
            self.assertEqual(owned_pool.activity[0].new_value, data_setup.ADMIN_USER)
            # group membership/ownership should be removed
            self.assertNotIn(group, user.groups)
            self.assertNotIn(user, group.users)
            self.assertFalse(group.has_owner(user))
            self.assertEqual(group.activity[-1].user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(group.activity[-1].field_name, u'User')
            self.assertEqual(group.activity[-1].action, u'Removed')
            self.assertEqual(group.activity[-1].old_value, user.user_name)
            self.assertEqual(group.activity[-1].new_value, None)

    def test_close_account_transfer_ownership(self):
        with session.begin():
            new_owner = data_setup.create_user()
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user)

        run_client(['bkr', 'remove-account', '--new-owner=%s' % new_owner.user_name, user.user_name])

        with session.begin():
            session.expire_all()
            self.assertEqual(system.owner, new_owner)

    def test_invalid_newowner_errors(self):
        """If an invalid username is passed as a new owner, we expect the
        command to error without changing the system."""
        invalid_username = u'asdfasdfasdf'
        with session.begin():
            user = data_setup.create_user()
            data_setup.create_system()
            self.assertFalse(session.query(User).filter_by(user_name=invalid_username).count())

        try:
            run_client(['bkr', 'remove-account', '--new-owner=%s' % invalid_username, user.user_name])
            self.fail('Expected client to fail due to invalid new owner')
        except ClientError as e:
            self.assertIn('Invalid user name for owner', e.stderr_output)
