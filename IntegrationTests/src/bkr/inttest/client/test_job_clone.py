
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client

class JobCloneTest(unittest.TestCase):

    def setUp(self):
        self.job = data_setup.create_completed_job()
        session.flush()

    def test_can_clone_job(self):
        out = run_client(['bkr', 'job-clone', self.job.t_id])
        self.assert_(out.startswith('Submitted:'))

    def test_can_clone_recipeset(self):
        out = run_client(['bkr', 'job-clone', self.job.recipesets[0].t_id])
        self.assert_(out.startswith('Submitted:'))
