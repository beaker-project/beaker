
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from bkr.server.model import session, SystemPermission
from bkr.inttest import data_setup
from bkr.inttest.client import run_client

class PolicyGrantTest(unittest.TestCase):

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
            group.users.append(user)
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
