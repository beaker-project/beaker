
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError

class JobListTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        jobs_to_generate = 2;
        self.products = [data_setup.create_product() for product in range(jobs_to_generate)]
        self.users = [data_setup.create_user() for user in range(jobs_to_generate)]
        self.jobs = [data_setup.create_completed_job(product=self.products[x], owner=self.users[x]) for x in range(jobs_to_generate)]

    def test_list_jobs_by_product(self):
        out = run_client(['bkr', 'job-list', '--product', self.products[0].name])
        self.assert_(self.jobs[0].t_id in out, [self.jobs[0].t_id, out])
        self.assertRaises(ClientError, run_client, ['bkr', 'job-list', '--product', 'foobar'])

    def test_list_jobs_by_owner(self):
        out = run_client(['bkr', 'job-list', '--owner', self.users[0].user_name])
        self.assert_(self.jobs[0].t_id in out, out)
        out = run_client(['bkr', 'job-list', '--owner', self.users[0].user_name, '--limit', '1'])
        self.assert_(len(out[0]) == 1, out)
        out = run_client(['bkr', 'job-list', '--owner', 'foobar'])
        self.assert_(self.jobs[0].t_id not in out, out)

    def test_list_jobs_by_whiteboard(self):
        out = run_client(['bkr', 'job-list', '--whiteboard', self.jobs[0].whiteboard])
        self.assert_(self.jobs[0].t_id in out, out)
        out = run_client(['bkr', 'job-list', '--whiteboard', 'foobar'])
        self.assert_(self.jobs[0].t_id not in out, out)
