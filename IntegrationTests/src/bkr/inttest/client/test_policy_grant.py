
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest2 as unittest
from bkr.server.model import session, SystemPermission
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class PolicyGrantTest(unittest.TestCase):

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
            group.users.append(user)
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
