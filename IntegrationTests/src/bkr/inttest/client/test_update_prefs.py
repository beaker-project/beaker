
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase

class UpdatePrefsTest(ClientTestCase):

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
            self.fail('should raise')
        except ClientError as e:
            self.assertIn('is same as before', e.stderr_output)

        run_client(['bkr', 'update-prefs', '--email=%s' % self.user2.email_address],
                config=self.client_config1)
        # This used to be forbidden, now it is allowed.
        with session.begin():
            session.refresh(self.user1)
            self.assertEquals(self.user1.email_address, self.user2.email_address)

        run_client(['bkr', 'update-prefs', '--email=foobar@example.com'],
                    config=self.client_config1)
        with session.begin():
            session.refresh(self.user1)
            self.assertEquals(self.user1.email_address, "foobar@example.com")
