
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client
import rdflib

class SystemDetailsTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()

    def test_system_details(self):
        out = run_client(['bkr', 'system-details', self.system.fqdn])
        g = rdflib.Graph()
        g.parse(data=out)
        self.assert_(len(g) > 0)
