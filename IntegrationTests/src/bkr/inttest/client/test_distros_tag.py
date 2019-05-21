
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase
from bkr.server.model import Distro

class DistrosTagTest(ClientTestCase):

    def test_tag_distro(self):
        with session.begin():
            self.distro = data_setup.create_distro()
        run_client(['bkr', 'distros-tag', '--name', self.distro.name, 'LOL'])
        with session.begin():
            session.refresh(self.distro)
            self.assert_(u'LOL' in self.distro.tags)

    def test_cannot_add_empty_tag(self):
        try:
            run_client(['bkr', 'distros-tag'])
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 2)
            self.assertIn('Please specify a tag', e.stderr_output)

    def test_cannot_add_tag_without_distro_name(self):
        try:
            run_client(['bkr', 'distros-tag', 'asdf'])
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 2)
            self.assertIn('If you really want to tag every distro in Beaker, use --name=%', e.stderr_output)

    def test_successful_add_tag_for_all_distros(self):
        with session.begin():
            self.distro = data_setup.create_distro()
        out = run_client(['bkr', 'distros-tag', '--name=%', 'addAll'])
        with session.begin():
            session.expire_all()
            for distro in Distro.query:
                self.assertIn(u'addAll', distro.tags)