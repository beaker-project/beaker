
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class JobCancelTest(unittest.TestCase):

    def setUp(self):
        self.job = data_setup.create_job()
        session.flush()

    def test_cannot_cancel_recipe(self):
        try:
            run_client(['bkr', 'job-cancel',
                    self.job.recipesets[0].recipes[0].t_id])
            fail('should raise')
        except ClientError, e:
            self.assertEquals(e.status, 1)
            self.assert_('Task type R is not stoppable'
                    in e.stderr_output, e.stderr_output)
