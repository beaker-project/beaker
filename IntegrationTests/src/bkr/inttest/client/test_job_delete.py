
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError

class JobDeleteTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.user = data_setup.create_user(password=u'asdf')
        self.job = data_setup.create_completed_job(owner=self.user)
        self.client_config = create_client_config(username=self.user.user_name,
                password='asdf')

    def test_delete_job(self):
        out = run_client(['bkr', 'job-delete', self.job.t_id],
                config=self.client_config)
        self.assert_(out.startswith('Jobs deleted:'), out)
        self.assert_(self.job.t_id in out, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-delete', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)
