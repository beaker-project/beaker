
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientTestCase
import json
import rdflib

class SystemDetailsTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()

    def test_system_details_xml(self):
        out = run_client(['bkr', 'system-details', self.system.fqdn])
        g = rdflib.Graph()
        g.parse(data=out)
        self.assert_(len(g) > 0)

    def test_system_details_json(self):
        out = run_client(['bkr', 'system-details', '--format', 'json',
                         self.system.fqdn])
        self.assert_(len(out) > 0)

        # Make sure you got what you asked for
        payload = json.loads(out)
        self.assertEquals(payload['fqdn'],
                          self.system.fqdn)
