
import unittest2 as unittest
from bkr.server.model import session
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1072127
    def test_password_not_set_on_server_side(self):
        # A user account might have a NULL password if the Beaker site is using 
        # Kerberos authentication, or if their account is new and the admin 
        # hasn't set a password yet.
        with session.begin():
            user = data_setup.create_user(password=None)
        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'whoami'], config=create_client_config(
                    username=user.user_name, password='irrelevant'))
        self.assertIn('Invalid username or password', assertion.exception.stderr_output)
