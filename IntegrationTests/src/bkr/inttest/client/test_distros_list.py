
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError
from bkr.server.model import LabControllerDistro

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=728022
    def test_filtering_by_lab_controller(self):
        good_lc = data_setup.create_labcontroller()
        bad_lc = data_setup.create_labcontroller()
        distro_in = data_setup.create_distro()
        distro_out = data_setup.create_distro()
        session.flush() # grumble
        distro_in.lab_controller_assocs[:] = [LabControllerDistro(lab_controller=good_lc)]
        distro_out.lab_controller_assocs[:] = [LabControllerDistro(lab_controller=bad_lc)]
        session.flush()
        output = run_client(['bkr', 'distros-list', '--labcontroller', good_lc.fqdn])
        self.assert_(any(distro_in.install_name in line for line in output.splitlines()))
        self.assert_(not any(distro_out.install_name in line for line in output.splitlines()))

    # https://bugzilla.redhat.com/show_bug.cgi?id=736989
    def test_filtering_by_treepath(self):
        lc = data_setup.create_labcontroller()
        distro_in = data_setup.create_distro()
        distro_out = data_setup.create_distro()
        session.flush()
        distro_in.lab_controller_assocs[:] = [LabControllerDistro(lab_controller=lc,
                tree_path='nfs://example.com/somewhere/')]
        distro_out.lab_controller_assocs[:] = [LabControllerDistro(lab_controller=lc,
                tree_path='nfs://example.com/nowhere/')]
        session.flush()
        output = run_client(['bkr', 'distros-list', '--treepath', '%somewhere%'])
        self.assert_(any(distro_in.install_name in line for line in output.splitlines()))
        self.assert_(not any(distro_out.install_name in line for line in output.splitlines()))
