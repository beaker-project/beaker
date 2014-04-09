
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class DistrosTagTest(unittest.TestCase):

    def test_tag_distro(self):
        with session.begin():
            self.distro = data_setup.create_distro()
        run_client(['bkr', 'distros-tag', '--name', self.distro.name, 'LOL'])
        with session.begin():
            session.refresh(self.distro)
            self.assert_(u'LOL' in self.distro.tags)
