
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, SystemPermission
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class PolicyGrantTest(ClientTestCase):

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system(shared=False)

    def test_grant_user(self):
        with session.begin():
            user = data_setup.create_user()
            self.assertFalse(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))
        run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--user', user.user_name])
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))

        # non-existent user
        try:
            run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                        '--permission', 'edit_system', '--user', 'idontexist'])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn("User 'idontexist' does not exist", e.stderr_output)

    def test_grant_group(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            group.add_member(user)
            self.assertFalse(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))
        run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--group', group.group_name])
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))

        # non-existent group
        try:
            run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                        '--permission', 'edit_system', '--group', 'idontexist'])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn("Group 'idontexist' does not exist", e.stderr_output)

    def test_grant_everybody(self):
        with session.begin():
            user = data_setup.create_user()
            self.assertFalse(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))
        run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--everybody'])
        with session.begin():
            session.expire_all()
            self.assertTrue(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))

    def test_grant_existing_permission(self):
        with session.begin():
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.edit_system, everybody=True)
        # should silently have no effect
        run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--everybody'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1021924
    def test_multiple_permissions_and_targets(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            # there is always the rule granting everybody view
            self.assertEquals(len(self.system.custom_access_policy.rules), 1)
        run_client(['bkr', 'policy-grant', '--system', self.system.fqdn,
                '--permission=reserve', '--permission=view_power',
                '--user', user.user_name, '--group', group.group_name])
        with session.begin():
            session.expire_all()
            self.assertEquals(len(self.system.custom_access_policy.rules), 5)

    def test_grant_policy_pool(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            user = data_setup.create_user()
            group = data_setup.create_group()
            group.add_member(user)
            user1 = data_setup.create_user()

        # group
        run_client(['bkr', 'policy-grant', '--pool', pool.name,
                    '--permission', 'edit_system', '--group', group.group_name])
        with session.begin():
            session.refresh(pool)
            self.assertTrue(pool.access_policy.grants(
                user, SystemPermission.edit_system))
        # non-existent group
        try:
            run_client(['bkr', 'policy-grant', '--pool', pool.name,
                        '--permission', 'edit_system', '--group', 'idontexist'])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn("Group 'idontexist' does not exist", e.stderr_output)

        # Everybody edit_system
        run_client(['bkr', 'policy-grant', '--pool', pool.name,
                '--permission', 'edit_system', '--everybody'])
        with session.begin():
            session.refresh(pool)
            self.assertTrue(pool.access_policy.grants(
                    user1, SystemPermission.edit_system))

        # test_multiple_permissions_and_targets
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            user1 = data_setup.create_user()
            group.add_member(user1)
        run_client(['bkr', 'policy-grant', '--pool', pool.name,
                    '--permission=reserve', '--permission=view_power', \
                    '--user', user.user_name, '--group', group.group_name])
        with session.begin():
            session.refresh(pool)
            self.assertTrue(pool.access_policy.grants(
                    user, SystemPermission.view_power))
            self.assertTrue(pool.access_policy.grants(
                    user, SystemPermission.reserve))
            self.assertTrue(pool.access_policy.grants(
                user1, SystemPermission.view_power))
            self.assertTrue(pool.access_policy.grants(
                    user1, SystemPermission.reserve))
        # non-existent pool
        try:
            run_client(['bkr', 'policy-grant', '--pool', 'idontexist',
                        '--permission=reserve', '--permission=view_power', \
                        '--user', user.user_name, '--group', group.group_name])
        except ClientError as e:
            self.assertIn("System pool idontexist does not exist", e.stderr_output)
