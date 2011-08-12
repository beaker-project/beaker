
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class DistrosListTest(unittest.TestCase):

    def setUp(self):
        self.distro = data_setup.create_distro()
        session.flush()

    def test_list_distro(self):
        output = run_client(['bkr', 'distros-list', '--name', self.distro.name])
        self.assert_(self.distro.name in output.splitlines()[1])

    def test_exits_with_error_if_none_match(self):
        try:
            run_client(['bkr', 'distros-list', '--name', self.distro.name,
                    '--tag', 'NOTEXIST'])
            fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertEqual(e.stderr_output, 'Nothing Matches\n')
