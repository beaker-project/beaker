
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase, create_client_config

class TestSystemPoolAdd(ClientTestCase):

    def test_add_systems_to_pool(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        with session.begin():
            pool = data_setup.create_system_pool(name=pool_name)
            s1 = data_setup.create_system()
            s2 = data_setup.create_system()
        run_client(['bkr', 'pool-add', '--pool', pool_name,
                    '--system', s1.fqdn,
                    '--system', s2.fqdn])
        with session.begin():
            session.refresh(pool)
            self.assertItemsEqual([s1, s2], pool.systems)

    def test_add_systems_to_non_existent_pool(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        with session.begin():
            s1 = data_setup.create_system()
        try:
            run_client(['bkr', 'pool-add', '--pool', pool_name,
                        '--system', s1.fqdn])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('System pool %s does not exist' % pool_name,
                          e.stderr_output)

    def test_add_nonexistent_system_to_pool(self):
        system_fqdn = data_setup.unique_name(u'mysystem%s')
        pool_name = data_setup.unique_name(u'mypool%s')
        with session.begin():
            pool = data_setup.create_system_pool(name=pool_name)
        try:
            run_client(['bkr', 'pool-add', '--pool', pool_name,
                        '--system', system_fqdn])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('System \'%s\' does not exist' %system_fqdn,
                          e.stderr_output)

    def test_add_systems_pool_privileges(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        with session.begin():
            system_owner = data_setup.create_user(password=u'password')
            pool_owner = data_setup.create_user(password=u'password')
            s1 = data_setup.create_system(owner=system_owner)
            pool = data_setup.create_system_pool(name=pool_name,
                                                 owning_user=pool_owner)
        try:
            run_client(['bkr', 'pool-add', '--pool', pool_name,
                        '--system', s1.fqdn],
                       config=create_client_config(
                           username=system_owner.user_name,
                           password='password'))
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('You do not have permission to'
                          ' add systems to pool %s' % pool_name,
                          e.stderr_output)

        try:
            run_client(['bkr', 'pool-add', '--pool', pool_name,
                        '--system', s1.fqdn],
                       config=create_client_config(
                           username=pool_owner.user_name,
                           password='password'))
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('You do not have permission to'
                          ' modify system %s' % s1.fqdn,
                          e.stderr_output)
