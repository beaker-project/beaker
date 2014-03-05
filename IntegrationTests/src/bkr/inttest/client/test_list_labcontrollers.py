
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest2 as unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client

class ListLabcontrollersTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.lc = data_setup.create_labcontroller()

    def test_list_lab_controller(self):
        out = run_client(['bkr', 'list-labcontrollers'])
        fqdns = out.splitlines()
        self.assertIn(self.lc.fqdn, fqdns)
