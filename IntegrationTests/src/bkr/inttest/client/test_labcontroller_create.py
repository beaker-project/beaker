
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, LabController, Group
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase, ClientError


class LabcontrollerCreateTest(ClientTestCase):

    def test_lab_controller_create(self):
        fqdn = data_setup.unique_name(u'mylab%s')
        run_client(['bkr', 'labcontroller-create',
                          '--fqdn', fqdn,
                          '--user', 'host/%s' % fqdn,
                          '--email', 'lab1@%s.com' % fqdn])
        with session.begin():
            lc = LabController.by_name(fqdn)
            self.assertEqual(lc.user.user_name, 'host/%s' % fqdn)
            self.assertEqual(lc.user.email_address, 'lab1@%s.com' % fqdn)
            self.assertIn(Group.by_name(u'lab_controller'), lc.user.groups)
        # can't create duplicate lab controller
        try:
            run_client(['bkr', 'labcontroller-create',
                              '--fqdn', fqdn,
                              '--user', 'host/%s' % fqdn,
                              '--email', 'lab1@%s.com' % fqdn])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn("Lab Controller %s already exists" % fqdn,
                          e.stderr_output)
