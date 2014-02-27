
import unittest2 as unittest
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, create_client_config, ClientError

class WhoAmITest(unittest.TestCase):

    def test_whoami(self):
        out = run_client(['bkr', 'whoami'])
        self.assertIn(data_setup.ADMIN_USER, out)

    def test_wrong_password(self):
        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'whoami'],
                    config=create_client_config(password='gotofail'))
        self.assertIn('Invalid username or password', assertion.exception.stderr_output)
