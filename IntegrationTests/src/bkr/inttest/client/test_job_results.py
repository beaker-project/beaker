
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client

class JobResultsTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_completed_job()

    def test_by_job(self):
        out = run_client(['bkr', 'job-results', self.job.t_id])
        self.assert_(out.startswith('<job '))

    def test_by_recipeset(self):
        out = run_client(['bkr', 'job-results', self.job.recipesets[0].t_id])
        self.assert_(out.startswith('<recipeSet '))

    def test_by_recipe(self):
        out = run_client(['bkr', 'job-results',
                self.job.recipesets[0].recipes[0].t_id])
        self.assert_(out.startswith('<recipe '))

    def test_by_recipetask(self):
        out = run_client(['bkr', 'job-results',
                self.job.recipesets[0].recipes[0].tasks[0].t_id])
        self.assert_(out.startswith('<task '))
