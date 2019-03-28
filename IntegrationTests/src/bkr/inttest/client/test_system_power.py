# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase, ClientError


class PowerSystemTest(ClientTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1181700
    def test_no_action(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)

        run_client(['bkr', 'system-power', '--action', 'none', '--clear-netboot',
                    system.fqdn])
        self.assertEqual(len(system.command_queue), 1)
        self.assertEqual(system.command_queue[0].action, 'clear_netboot')

    def test_reboot_action(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
        run_client(['bkr', 'system-power', '--action',
                    'reboot', '--clear-netboot', system.fqdn])
        self.assertEqual(len(system.command_queue), 3)
        self.assertEqual(system.command_queue[0].action, 'on')
        self.assertEqual(system.command_queue[1].action, 'off')
        self.assertEqual(system.command_queue[2].action, 'clear_netboot')

    def test_force(self):
        with session.begin():
            user = data_setup.create_user()
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            system.user = user
        try:
            run_client(['bkr', 'system-power', '--action',
                        'reboot', system.fqdn])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn('You are not the current user of the system',
                          e.stderr_output)
        run_client(['bkr', 'system-power', '--action',
                    'interrupt', '--force', system.fqdn])
        self.assertEqual(len(system.command_queue), 1)
        self.assertEqual(system.command_queue[0].action, 'interrupt')
