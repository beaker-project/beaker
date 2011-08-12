
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, create_client_config

class JobDeleteTest(unittest.TestCase):

    def setUp(self):
        self.user = data_setup.create_user(password=u'asdf')
        self.job = data_setup.create_completed_job(owner=self.user)
        self.client_config = create_client_config(username=self.user.user_name,
                password='asdf')
        session.flush()

    def test_delete_job(self):
        out = run_client(['bkr', 'job-delete', self.job.t_id],
                config=self.client_config)
        self.assert_(out.startswith('Jobs deleted:'), out)
        self.assert_(self.job.t_id in out, out)
