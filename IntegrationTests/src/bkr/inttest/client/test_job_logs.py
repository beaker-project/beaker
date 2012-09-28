
import unittest
import urlparse
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.client import run_client, ClientError

class JobLogsTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_completed_job()
        self.base = urlparse.urljoin(get_server_base(), '/logs/')

    def test_by_job(self):
        out = run_client(['bkr', 'job-logs', self.job.t_id])
        logs = out.splitlines()
        self.assert_(logs[0].startswith(self.base), logs[0])
        self.assert_(logs[0].endswith('recipe_path/dummy.txt'), logs[0])
        self.assert_(logs[1].startswith(self.base), logs[1])
        self.assert_(logs[1].endswith('tasks/dummy.txt'), logs[1])
        self.assert_(logs[2].startswith(self.base), logs[2])
        self.assert_(logs[2].endswith('result.txt'), logs[2])

    def test_by_recipeset(self):
        out = run_client(['bkr', 'job-logs', self.job.recipesets[0].t_id])
        logs = out.splitlines()
        self.assert_(logs[0].startswith(self.base), logs[0])
        self.assert_(logs[0].endswith('recipe_path/dummy.txt'), logs[0])
        self.assert_(logs[1].startswith(self.base), logs[1])
        self.assert_(logs[1].endswith('tasks/dummy.txt'), logs[1])
        self.assert_(logs[2].startswith(self.base), logs[2])
        self.assert_(logs[2].endswith('result.txt'), logs[2])

    def test_by_recipe(self):
        out = run_client(['bkr', 'job-logs',
                self.job.recipesets[0].recipes[0].t_id])
        logs = out.splitlines()
        self.assert_(logs[0].startswith(self.base), logs[0])
        self.assert_(logs[0].endswith('recipe_path/dummy.txt'), logs[0])
        self.assert_(logs[1].startswith(self.base), logs[1])
        self.assert_(logs[1].endswith('tasks/dummy.txt'), logs[1])
        self.assert_(logs[2].startswith(self.base), logs[2])
        self.assert_(logs[2].endswith('result.txt'), logs[2])

    def test_by_task(self):
        out = run_client(['bkr', 'job-logs',
                self.job.recipesets[0].recipes[0].tasks[0].t_id])
        logs = out.splitlines()
        self.assert_(logs[0].startswith(self.base), logs[0])
        self.assert_(logs[0].endswith('tasks/dummy.txt'), logs[0])
        self.assert_(logs[1].startswith(self.base), logs[1])
        self.assert_(logs[1].endswith('result.txt'), logs[1])

    def test_by_taskresult(self):
        out = run_client(['bkr', 'job-logs',
                self.job.recipesets[0].recipes[0].tasks[0].results[0].t_id])
        logs = out.splitlines()
        self.assert_(logs[0].startswith(self.base), logs[0])
        self.assert_(logs[0].endswith('result.txt'), logs[0])

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-logs', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)
