
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class DistrosEditVersionTest(unittest.TestCase):

    def test_edit_distro_version(self):
        with session.begin():
            distro = data_setup.create_distro()
        run_client(['bkr', 'distros-edit-version', '--name', distro.name,
                'SillyVersion2.1'])
        with session.begin():
            session.refresh(distro)
            self.assertEquals(distro.osversion.osmajor.osmajor, u'SillyVersion2')
            self.assertEquals(distro.osversion.osminor, u'1')
