
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import datetime
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError, ClientTestCase
from bkr.server.model import Distro

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

    def test_exits_with_error_if_none_match(self):
        try:
            run_client(['bkr', 'distros-list', '--name', self.distro.name,
                    '--tag', 'NOTEXIST'])
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assertEqual(e.stderr_output, 'Nothing Matches\n')

    def test_output_is_ordered_by_date_created(self):
        with session.begin():
            # Insert them in reverse order (oldest last), just because the most
            # likely regression here is that we aren't sorting at all and thus
            # the output is in database insertion order. So this proves that's
            # not happening.
            new_distro = data_setup.create_distro(date_created=datetime.datetime(2021, 1, 1, 0, 0))
            data_setup.create_distro_tree(distro=new_distro)
            old_distro = data_setup.create_distro(date_created=datetime.datetime(2004, 1, 1, 0, 0))
            data_setup.create_distro_tree(distro=old_distro)
        output = run_client(['bkr', 'distros-list', '--format=json'])
        with session.begin():
            session.expire_all()
            returned_distros = [Distro.query.get(entry['distro_id'])
                    for entry in json.loads(output)]
            for i in range(1, len(returned_distros)):
                self.assertGreaterEqual(
                        returned_distros[i - 1].date_created,
                        returned_distros[i].date_created)
