
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase

class SystemDeleteTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.user = data_setup.create_user(password=u'asdf')
        self.user2 = data_setup.create_user(password=u'qwerty')

        self.system = data_setup.create_system(owner=self.user,
                lab_controller=data_setup.create_labcontroller())

        self.client_config = create_client_config(username=self.user.user_name,
                password='asdf')
        self.client_config2 = create_client_config(username=self.user2.user_name,
                password='qwerty')
        self.client_config3 = create_client_config()

    def test_user_cannot_delete_system(self):
        # user2 should not be able to delete system
        try:
            out = run_client(['bkr', 'system-delete', self.system.fqdn],
                    config=self.client_config2)
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assert_(e.stderr_output.find("you don't own") != -1)

    def test_user_can_delete_system(self):
        # user1 should be able to delete system
        out = run_client(['bkr', 'system-delete', self.system.fqdn],
                config=self.client_config)
        self.assert_(out.startswith('Deleted %s' % self.system.fqdn), out)

    def test_admin_can_delete_system(self):
        # admin should be able to delete system
        out = run_client(['bkr', 'system-delete', self.system.fqdn],
                config=self.client_config3)
        self.assert_(out.startswith('Deleted %s' % self.system.fqdn), out)

    def test_cannot_delete_system_which_has_been_used_for_recipes(self):
        with session.begin():
            job = data_setup.create_job()
            data_setup.mark_job_complete(job, system=self.system)

        try:
            out = run_client(['bkr', 'system-delete', self.system.fqdn],
                    config=self.client_config)
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assert_(e.stderr_output.find('with reservations') != -1)

    def test_cannot_delete_nonexistent_system(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        try:
            run_client(['bkr', 'system-delete', fqdn])
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assertIn("System %s does not exist" % fqdn, e.stderr_output)
