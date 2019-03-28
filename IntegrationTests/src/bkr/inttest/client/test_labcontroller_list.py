
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientTestCase

class LabcontrollerListTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.removed_lc = data_setup.create_labcontroller()
        self.removed_lc.removed = datetime.utcnow()

    def test_list_lab_controller(self):
        out = run_client(['bkr', 'labcontroller-list'])
        fqdns = out.splitlines()
        self.assertIn(self.lc.fqdn, fqdns)
        self.assertNotIn(self.removed_lc.fqdn, fqdns)

    def test_old_command_list_labcontrollers_still_works(self):
        out = run_client(['bkr', 'list-labcontrollers'])
        fqdns = out.splitlines()
        self.assertIn(self.lc.fqdn, fqdns)
        self.assertNotIn(self.removed_lc.fqdn, fqdns)
