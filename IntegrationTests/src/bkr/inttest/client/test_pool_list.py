from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase


class PoolList(ClientTestCase):

    def test_list_pools(self):
        with session.begin():
            pool1 = data_setup.create_system_pool()
            pool2 = data_setup.create_system_pool()
        out = run_client(['bkr', 'pool-list'])
        self.assertIn(pool1.name, out)
        self.assertIn(pool2.name, out)

    def test_list_pools_by_owner(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            pool1 = data_setup.create_system_pool(owning_user=user1)
            pool2 = data_setup.create_system_pool(owning_user=user2)
        out = run_client(['bkr', 'pool-list', '--owner', str(user1.user_name)])
        self.assertIn(pool1.name, out)
        self.assertNotIn(pool2.name, out)

    def test_list_pools_by_ownergroup(self):
        with session.begin():
            group1 = data_setup.create_group()
            pool1 = data_setup.create_system_pool(owning_group=group1)
            group2 = data_setup.create_group()
            pool2 = data_setup.create_system_pool(owning_group=group2)
        out = run_client(['bkr', 'pool-list',
                          '--owning-group', str(group1.group_name)])
        self.assertIn(pool1.name, out)
        self.assertNotIn(pool2.name, out)

    def test_list_pools_limit(self):
        with session.begin():
            data_setup.create_system_pool()
            data_setup.create_system_pool()
        out1 = run_client(['bkr', 'pool-list'])
        pools1 = out1.split()
        out2 = run_client(['bkr', 'pool-list', '--limit=1'])
        pools2 = out2.split()
        self.assertEquals(len(pools2), 1)
        self.assertEquals(pools1[0], pools2[0])

    def test_list_pools_by_owner_and_group(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
        try:
            run_client(['bkr', 'pool-list',
                        '--owner', str(user.user_name),
                        '--owning-group', str(group.group_name)])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('Only one of --owner or --owning-group may be specified',
                          e.stderr_output)

    def test_list_pool_by_owner_that_has_no_pool(self):
        with session.begin():
            user = data_setup.create_user()
        try:
            run_client(['bkr', 'pool-list', '--owner', str(user.user_name)])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assertIn('Nothing Matches', e.stderr_output)

    def test_list_pool_by_group_that_has_no_pool(self):
        with session.begin():
            group = data_setup.create_group()
        try:
            run_client(['bkr', 'pool-list', '--owning-group', str(group.group_name)])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assertIn('Nothing Matches', e.stderr_output)
