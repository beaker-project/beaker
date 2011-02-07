
import unittest
from bkr.server.model import System, LabInfo
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.tools.delete_system import delete_system

class DeleteSystemTest(unittest.TestCase):

    def setUp(self):
        self.system = data_setup.create_system()
        self.system.labinfo = LabInfo()
        self.system.labinfo.weight = 1
        session.flush()

    def test_can_delete_system(self):
        delete_system(self.system.fqdn)
        self.assert_(System.query().get(self.system.id) is None)

    def test_dry_run_rolls_back(self):
        delete_system(self.system.fqdn, dry_run=True)
        self.assert_(System.query().get(self.system.id) is not None)

    def test_cannot_delete_system_which_has_been_used_for_recipes(self):
        job = data_setup.create_job()
        data_setup.mark_job_complete(job, system=self.system)
        session.flush()

        try:
            delete_system(self.system.fqdn)
            self.fail('should raise')
        except ValueError:
            pass
        self.assert_(System.query().get(self.system.id) is not None)
