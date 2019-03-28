from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase, ClientError

class PoolSystems(ClientTestCase):

    def test_list_systems_in_a_pool_with_format_list(self):
        with session.begin():
            system1 = data_setup.create_system()
            system2 = data_setup.create_system()
            pool = data_setup.create_system_pool(systems=[system1, system2])

        out = run_client(['bkr', 'pool-systems', pool.name])
        self.assertIn(system1.fqdn, out)
        self.assertIn(system2.fqdn, out)

    def test_list_systems_in_a_pool_with_format_json(self):
        with session.begin():
            system1 = data_setup.create_system()
            system2 = data_setup.create_system()
            pool = data_setup.create_system_pool(systems=[system1, system2])

        out = run_client(['bkr', 'pool-systems', pool.name,
                      '--format', 'json'])
        self.assertIn(system1.fqdn, out)
        self.assertIn(system2.fqdn, out)

    def test_list_systems_nonexistent_pool(self):
        pool_name = data_setup.unique_name(u'mypool%s')
        try:
            out = run_client(['bkr', 'pool-systems',
                              pool_name])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('System pool %s does not exist' % pool_name,
                         e.stderr_output)

    def test_list_systems_CLI_no_given_poolname(self):
        try:
            out = run_client(['bkr', 'pool-systems'])
            self.fail('Must fail or die')
        except ClientError as e:
                self.assertIn('Exactly one pool name must be specified',
                              e.stderr_output)
