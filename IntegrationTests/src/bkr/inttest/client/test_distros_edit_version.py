# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase


class DistrosEditVersionTest(ClientTestCase):

    def test_edit_distro_version(self):
        with session.begin():
            distro = data_setup.create_distro()
        run_client(['bkr', 'distros-edit-version', '--name', distro.name,
                    'SillyVersion2.1'])
        with session.begin():
            session.refresh(distro)
            self.assertEquals(distro.osversion.osmajor.osmajor, u'SillyVersion2')
            self.assertEquals(distro.osversion.osminor, u'1')
