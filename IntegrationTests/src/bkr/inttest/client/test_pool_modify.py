
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import (run_client, ClientError, ClientTestCase,
                                create_client_config)

class PoolModifyTest(ClientTestCase):

    def test_pool_modify_insufficient_priv(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user(password=u'password')
            pool = data_setup.create_system_pool(owning_user=user1)
        try:
            run_client(['bkr', 'pool-modify',
                        '--name', 'arandomnewname',
                        pool.name],
                       config=create_client_config(
                           username=user2.user_name, password='password'))
            self.fail('Must error out')
        except ClientError as e:
            self.assertIn('Cannot edit system pool',
                          e.stderr_output)

    def test_pool_change_name(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            pool1 = data_setup.create_system_pool()
        new_name = data_setup.unique_name(u'newpool%s')
        run_client(['bkr', 'pool-modify',
                    '--name', new_name,
                    pool.name])
        with session.begin():
            session.refresh(pool)
            self.assertEquals(pool.name, new_name)

        # rename to an existing pool will error out
        try:
            run_client(['bkr', 'pool-modify',
                        '--name', pool1.name,
                        pool.name])
            self.fail('Must error out')
        except ClientError as e:
            self.assertIn('System pool %s already exists' % pool1.name,
                          e.stderr_output)

    def test_pool_change_description(self):
        with session.begin():
            pool = data_setup.create_system_pool()
        run_client(['bkr', 'pool-modify',
                    '--description', 'Oh my pool',
                    pool.name])
        with session.begin():
            session.refresh(pool)
            self.assertEquals(pool.description, 'Oh my pool')

    def test_pool_change_owner_to_group(self):
        with session.begin():
            group = data_setup.create_group()
            group_name = group.group_name
            pool_name = data_setup.unique_name(u'pool%s')
            pool = data_setup.create_system_pool(name=pool_name)
        run_client(['bkr', 'pool-modify',
                    '--owning-group', group_name,
                    pool_name])
        with session.begin():
            session.refresh(pool)
            self.assertTrue(pool.owning_group, group)
            self.assertFalse(pool.owning_user)

    def test_pool_change_owner_to_another_user(self):
        with session.begin():
            user = data_setup.create_user()
            new_owner = user.user_name
            pool = data_setup.create_system_pool()
        run_client(['bkr', 'pool-modify',
                    '--owner', new_owner,
                    pool.name])
        with session.begin():
            session.refresh(pool)
            self.assertTrue(pool.owning_user, user)
