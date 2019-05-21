
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, SystemPermission
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class PolicyRevokeTest(ClientTestCase):

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system(shared=False)

    def test_revoke_user(self):
        with session.begin():
            user = data_setup.create_user()
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.edit_system, user=user)
            self.assertTrue(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))
        run_client(['bkr', 'policy-revoke', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--user', user.user_name])
        with session.begin():
            session.expire_all()
            self.assertFalse(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))

    def test_revoke_group(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            group.add_member(user)
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.edit_system, group=group)
            self.assertTrue(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))
        run_client(['bkr', 'policy-revoke', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--group', group.group_name])
        with session.begin():
            session.expire_all()
            self.assertFalse(self.system.custom_access_policy.grants(
                    user, SystemPermission.edit_system))

    def test_revoke_everybody(self):
        with session.begin():
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.edit_system, everybody=True)
            self.assertTrue(self.system.custom_access_policy.grants_everybody(
                    SystemPermission.edit_system))
        run_client(['bkr', 'policy-revoke', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--everybody'])
        with session.begin():
            session.expire_all()
            self.assertFalse(self.system.custom_access_policy.grants_everybody(
                    SystemPermission.edit_system))

    def test_revoke_nonexistent_permission(self):
        with session.begin():
            self.assertFalse(self.system.custom_access_policy.grants_everybody(
                    SystemPermission.edit_system))
        # should silently have no effect
        run_client(['bkr', 'policy-revoke', '--system', self.system.fqdn,
                '--permission', 'edit_system', '--everybody'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1021924
    def test_multiple_permissions_and_targets(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            pol = self.system.custom_access_policy
            pol.add_rule(SystemPermission.reserve, user=user)
            pol.add_rule(SystemPermission.view_power, user=user)
            pol.add_rule(SystemPermission.reserve, group=group)
            pol.add_rule(SystemPermission.view_power, group=group)
            # there is always the rule granting everybody view
            self.assertEquals(len(self.system.custom_access_policy.rules), 5)
        run_client(['bkr', 'policy-revoke', '--system', self.system.fqdn,
                '--permission=reserve', '--permission=view_power',
                '--user', user.user_name, '--group', group.group_name])
        with session.begin():
            session.expire_all()
            self.assertEquals(len(self.system.custom_access_policy.rules), 1)

    def test_revoke_policy_pool(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            user = data_setup.create_user()
            user1 = data_setup.create_user()
            group = data_setup.create_group()
            group.add_member(user1)

            pol = pool.access_policy
            pol.add_rule(SystemPermission.reserve, user=user)
            pol.add_rule(SystemPermission.view_power, user=user)
            pol.add_rule(SystemPermission.reserve, group=group)
            pol.add_rule(SystemPermission.view_power, group=group)

        # revoke edit_system from group
        run_client(['bkr', 'policy-revoke', '--pool', pool.name,
                    '--permission', 'view_power', '--group', group.group_name])
        with session.begin():
            session.refresh(pool)
            self.assertFalse(pool.access_policy.grants(
                user1, SystemPermission.edit_system))

        # test_multiple_permissions_and_targets
        run_client(['bkr', 'policy-revoke', '--pool', pool.name,
                    '--permission=reserve', '--permission=view_power', \
                    '--user', user.user_name, '--group', group.group_name])
        with session.begin():
            session.refresh(pool)
            self.assertFalse(pool.access_policy.grants(
                    user, SystemPermission.view_power))
            self.assertFalse(pool.access_policy.grants(
                    user, SystemPermission.reserve))
            self.assertFalse(pool.access_policy.grants(
                user1, SystemPermission.view_power))
            self.assertFalse(pool.access_policy.grants(
                    user1, SystemPermission.reserve))

        # this should still exist
        with session.begin():
            session.refresh(pool)
            self.assertTrue(pool.access_policy.grants(
                user, SystemPermission.view))

        # non-existent pool
        try:
            run_client(['bkr', 'policy-revoke', '--pool', 'idontexist',
                        '--permission=reserve', '--permission=view_power', \
                        '--user', user.user_name, '--group', group.group_name])
        except ClientError as e:
            self.assertIn("System pool idontexist does not exist", e.stderr_output)
