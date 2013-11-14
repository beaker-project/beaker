
import unittest2 as unittest
from bkr.server.model import session, SystemPermission
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError
import bkr.client.json_compat as json
from prettytable import PrettyTable

class PolicyListTest(unittest.TestCase):

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system(shared=False)
            self.system_public = data_setup.create_system(shared=False)

    def gen_expected_pretty_table(self, rows):
        table = PrettyTable(['Permission', 'User', 'Group', 'Everybody'])
        for row in rows:
            table.add_row(row)
        return table.get_string()

    def test_list_policy(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            group = data_setup.create_group()

            self.system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user1)
            self.system.custom_access_policy.add_rule(
                permission=SystemPermission.control_system, user=user2)
            self.system.custom_access_policy.add_rule(
                permission=SystemPermission.control_system, group=group)
            self.system_public.custom_access_policy.add_rule(
                permission=SystemPermission.control_system, everybody=True)


        # print the policies as a list
        out = run_client(['bkr', 'policy-list', '--system', self.system.fqdn])
        expected_output = self.gen_expected_pretty_table(
            (['control_system', 'X', group.group_name, 'No'],
             ['control_system', user2.user_name, 'X', 'No'],
             ['edit_system', user1.user_name, 'X', 'No'])) + '\n'
        self.assertEquals(out, expected_output)

        # For the second system
        out = run_client(['bkr', 'policy-list', '--system', self.system_public.fqdn,
                          '--format','tabular'])
        expected_output = self.gen_expected_pretty_table(
            (['control_system', 'X', 'X', 'Yes'],)) + '\n'

        self.assertEquals(out, expected_output)

        # print the policies as JSON object
        out = run_client(['bkr', 'policy-list', '--system', self.system.fqdn,
                          '--format','json'])
        out = json.loads(out)
        self.assertEquals(len(out['rules']), 3)

    def test_list_policy_non_existent_system(self):

        try:
            out = run_client(['bkr', 'policy-list', '--system', 'ineverexisted'])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('System not found', e.stderr_output)
