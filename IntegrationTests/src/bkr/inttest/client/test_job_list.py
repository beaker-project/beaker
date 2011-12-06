
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config

class JobListTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.product = data_setup.create_product()
        self.job = data_setup.create_completed_job(product=self.product)

    def test_list_jobs_by_product(self):
        out = run_client(['bkr', 'job-list', '--product', self.product.name])
        self.assert_(self.job.t_id in out, out)
