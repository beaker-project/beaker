
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError

class DistrosVerifyTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.dodgy_lc = data_setup.create_labcontroller(
                fqdn=u'dodgylc.example.invalid')
        self.distro = data_setup.create_distro()
        session.flush() # XXX why is this necessary?
        self.distro.lab_controllers.remove(self.dodgy_lc)

    def test_verify_distro(self):
        output = run_client(['bkr', 'distros-verify', '--name', self.distro.name])
        lines = output.splitlines()
        self.assert_(lines[0].startswith(self.distro.name))
        self.assertEquals(lines[1], "missing from labs ['dodgylc.example.invalid']")
