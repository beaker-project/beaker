
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client
from bkr.server.model import Job

class MachineTestTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        data_setup.create_task(name=u'/distribution/inventory')
        self.distro = data_setup.create_distro(tags=[u'STABLE'])
        data_setup.create_distro_tree(distro=self.distro)

    def test_machine_test(self):
        fqdn = 'system1.example.invalid'
        out = run_client(['bkr', 'machine-test', '--inventory',
                '--machine', fqdn,
                '--family', self.distro.osversion.osmajor.osmajor])
        self.assert_(out.startswith('Submitted:'), out)
        with session.begin():
            new_job = Job.query.order_by(Job.id.desc()).first()
            self.assertEqual(new_job.whiteboard, u'Test system1.example.invalid')
            tasks = new_job.recipesets[0].recipes[0].tasks
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[0].task.name, u'/distribution/install')
            self.assertEqual(tasks[1].task.name, u'/distribution/inventory')
