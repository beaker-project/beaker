import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError

class UpdatePrefsTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.user1 = data_setup.create_user(password=u'asdf')
        self.user2 = data_setup.create_user(password=u'qwerty')

        self.client_config1 = create_client_config(username=self.user1.user_name,
                password='asdf')
        self.client_config2 = create_client_config(username=self.user2.user_name,
                password='qwerty')

    def test_user_edit_email(self):
        try:
            run_client(['bkr', 'update-prefs', '--email=%s' % self.user1.email_address],
                       config=self.client_config1)
            fail('should raise')
        except ClientError, e:
            self.assert_('is same as before' in e.stderr_output)

        try:
            run_client(['bkr', 'update-prefs', '--email=%s' % self.user2.email_address],
                       config=self.client_config1)
            fail('should raise')
        except ClientError, e:
            self.assert_('is not unique' in e.stderr_output)

        run_client(['bkr', 'update-prefs', '--email=foobar@example.com'],
                    config=self.client_config1)
        with session.begin():
            session.refresh(self.user1)
            self.assert_(self.user1.email_address == "foobar@example.com")
