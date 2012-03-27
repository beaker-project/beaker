
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class DistrosUntagTest(unittest.TestCase):

    def test_untag_distro(self):
        with session.begin():
            self.distro = data_setup.create_distro(tags=[u'RELEASED', u'STABLE'])
        run_client(['bkr', 'distros-untag', '--name', self.distro.name, 'RELEASED'])
        with session.begin():
            session.refresh(self.distro)
            self.assertEquals(self.distro.tags, [u'STABLE'])
