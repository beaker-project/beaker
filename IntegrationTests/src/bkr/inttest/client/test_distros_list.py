
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError, ClientTestCase
from bkr.server.model import LabControllerDistroTree

class DistrosListTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
        data_setup.create_distro_tree(distro=self.distro)

    def test_list_distro(self):
        output = run_client(['bkr', 'distros-list', '--format=json', '--name', self.distro.name])
        distros = json.loads(output)
        self.assertEquals(len(distros), 1)
        self.assertEquals(distros[0]['distro_id'], self.distro.id)
        self.assertEquals(distros[0]['distro_name'], self.distro.name)

    def test_list_distro_id(self):
        output = run_client(['bkr', 'distros-list', '--format=json', '--distro-id', str(self.distro.id)])
        distros = json.loads(output)
        self.assertEquals(len(distros), 1)
        self.assertEquals(distros[0]['distro_id'], self.distro.id)
        self.assertEquals(distros[0]['distro_name'], self.distro.name)

    def test_list_distro_limit(self):
        output = run_client(['bkr', 'distros-list', '--format=json', '--limit=1'])
        distros = json.loads(output)
        self.assertEquals(len(distros), 1)
        self.assertEquals(distros[0]['distro_id'], self.distro.id)
        self.assertEquals(distros[0]['distro_name'], self.distro.name)

    def test_exits_with_error_if_none_match(self):
        try:
            run_client(['bkr', 'distros-list', '--name', self.distro.name,
                    '--tag', 'NOTEXIST'])
            fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertEqual(e.stderr_output, 'Nothing Matches\n')
