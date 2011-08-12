
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class DistrosEditVersionTest(unittest.TestCase):

    def test_edit_distro_version(self):
        distro = data_setup.create_distro()
        session.flush()
        run_client(['bkr', 'distros-edit-version', '--name', distro.name,
                'SillyVersion2.1'])
        session.refresh(distro)
        self.assertEquals(distro.osversion.osmajor.osmajor, u'SillyVersion2')
        self.assertEquals(distro.osversion.osminor, u'1')
