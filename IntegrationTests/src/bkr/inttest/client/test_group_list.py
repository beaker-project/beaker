from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class GroupList(ClientTestCase):

    def test_list_groups(self):
        with session.begin():
            group1 = data_setup.create_group()
            group2 = data_setup.create_group()
        out = run_client(['bkr', 'group-list'])
        self.assertIn(group1.group_name, out)
        self.assertIn(group2.group_name, out)

    def test_list_groups_by_owner(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            group1 = data_setup.create_group(owner=user1)
            group2 = data_setup.create_group(owner=user2)
        out = run_client(['bkr', 'group-list', '--owner', str(user1.user_name)])
        self.assertIn(group1.group_name, out)
        self.assertNotIn(group2.group_name, out)

    def test_list_groups_limit(self):
        with session.begin():
            data_setup.create_group()
            data_setup.create_group()
        out1 = run_client(['bkr', 'group-list'])
        groups1 = out1.split()
        out2 = run_client(['bkr', 'group-list', '--limit=1'])
        groups2 = out2.split()
        self.assertEquals(len(groups2), 1)
        self.assertEquals(groups1[0], groups2[0])

    def test_list_group_of_owner_that_has_no_group(self):
        with session.begin():
            user = data_setup.create_user()
        try:
            run_client(['bkr', 'group-list', '--owner', str(user.user_name)])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assertIn('Nothing Matches', e.stderr_output)
