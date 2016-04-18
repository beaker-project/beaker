
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, SystemPool
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class CreateSystemPool(ClientTestCase):

    def test_create_pool_defaults(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        run_client(['bkr', 'pool-create', pool_name])

        with session.begin():
            pool = SystemPool.by_name(pool_name)
            self.assertFalse(pool.description)
            self.assertFalse(pool.owning_group)
            self.assertTrue(pool.owning_user.user_name, "admin")
            self.assertEquals(pool.activity[-1].field_name, u'Pool')
            self.assertEquals(pool.activity[-1].action, u'Created')
            self.assertEquals(pool.activity[-1].new_value, pool_name)
        # duplicate
        try:
            run_client(['bkr', 'pool-create', pool_name])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn("System pool with name u'%s' already exists" % pool_name,
                          e.stderr_output)

    def test_create_pool_set_description(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        run_client(['bkr', 'pool-create',
                    '--description', 'My Pool',
                    pool_name])

        with session.begin():
            pool = SystemPool.by_name(pool_name)
            self.assertEquals(pool.description, 'My Pool')

    def test_create_pool_set_owner(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        owner = data_setup.create_user()
        run_client(['bkr', 'pool-create',
                    '--owner', owner.user_name,
                    pool_name])
        with session.begin():
            p = SystemPool.by_name(pool_name)
            self.assertFalse(p.owning_group)
            self.assertTrue(p.owning_user.user_name,
                            owner.user_name)

        pool_name = data_setup.unique_name(u'mypool%s')

        owning_group = data_setup.create_group()
        run_client(['bkr', 'pool-create',
                    '--owning-group', owning_group.group_name,
                    pool_name])
        with session.begin():
            p = SystemPool.by_name(pool_name)
            self.assertTrue(p.owning_group, owning_group)
            self.assertFalse(p.owning_user)

        # specifying both should error out
        try:
            run_client(['bkr', 'pool-create',
                        '--owner', owner.user_name,
                        '--owning-group', owning_group.group_name,
                    pool_name])
            self.fail('Must error out')
        except ClientError as e:
            self.assertIn('Only one of owner or owning-group must be specified',
                          e.stderr_output)
