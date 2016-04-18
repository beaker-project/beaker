
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase, \
    create_client_config

class TestSystemPoolRemove(ClientTestCase):

    def test_remove_systems_from_pool(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        with session.begin():
            s1 = data_setup.create_system()
            s2 = data_setup.create_system()
            s3 = data_setup.create_system()
            s4 = data_setup.create_system()
            pool = data_setup.create_system_pool(name=pool_name,
                                                 systems=[s1, s2, s3])
        run_client(['bkr', 'pool-remove', '--pool', pool_name,
                    '--system', s1.fqdn,
                    '--system', s2.fqdn])
        with session.begin():
            session.refresh(pool)
            self.assertIn(s3, pool.systems)

        # remove system from a pool of which it is not a member of
        try:
            run_client(['bkr', 'pool-remove', '--pool', pool_name,
                        '--system', s4.fqdn])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('System %s is not in pool %s' % (s4.fqdn, pool_name),
                          e.stderr_output)

    def test_remove_system_from_non_existent_pool(self):
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

    def test_remove_systems_pool_privileges(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        with session.begin():
            system_owner = data_setup.create_user(password=u'password')
            pool_owner = data_setup.create_user(password=u'password')
            random_user = data_setup.create_user(password=u'password')
            s1 = data_setup.create_system(owner=system_owner)
            s2 = data_setup.create_system(owner=system_owner)
            s3 = data_setup.create_system(owner=system_owner)
            pool = data_setup.create_system_pool(name=pool_name,
                                                 owning_user=pool_owner,
                                                 systems=[s1, s2, s3]
                                             )
        run_client(['bkr', 'pool-remove', '--pool', pool_name,
                    '--system', s1.fqdn],
                   config=create_client_config(
                       username=system_owner.user_name,
                       password='password'))
        with session.begin():
            session.refresh(pool)
            self.assertNotIn(s1, pool.systems)

        run_client(['bkr', 'pool-remove', '--pool', pool_name,
                    '--system', s2.fqdn],
                   config=create_client_config(
                       username=pool_owner.user_name,
                       password='password'))
        with session.begin():
            session.refresh(pool)
            self.assertNotIn(s2, pool.systems)


        try:
            run_client(['bkr', 'pool-remove', '--pool', pool_name,
                        '--system', s3.fqdn],
                       config=create_client_config(
                           username=random_user.user_name,
                           password='password'))
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('You do not have permission to modify system %s'
                               'or remove systems from pool %s' % (s3.fqdn, pool_name),
                          e.stderr_output)
