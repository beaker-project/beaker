
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase

class DistrosUntagTest(ClientTestCase):

    def test_untag_distro(self):
        with session.begin():
            self.distro = data_setup.create_distro(tags=[u'RELEASED', u'STABLE'])
        run_client(['bkr', 'distros-untag', '--name', self.distro.name, 'RELEASED'])
        with session.begin():
            session.refresh(self.distro)
            self.assertEquals(self.distro.tags, [u'STABLE'])
