
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class DistrosTagTest(unittest.TestCase):

    def test_tag_distro(self):
        self.distro = data_setup.create_distro()
        session.flush()
        run_client(['bkr', 'distros-tag', '--name', self.distro.name, 'LOL'])
        session.refresh(self.distro)
        self.assert_(u'LOL' in self.distro.tags)
