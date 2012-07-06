
import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError

class JobCloneTest(unittest.TestCase):

    @classmethod
    @with_transaction
    def setupClass(cls):
        cls.job = data_setup.create_completed_job()

    def test_can_clone_job(self):
        out = run_client(['bkr', 'job-clone', self.job.t_id])
        self.assert_(out.startswith('Submitted:'))

    def test_can_clone_recipeset(self):
        out = run_client(['bkr', 'job-clone', self.job.recipesets[0].t_id])
        self.assert_(out.startswith('Submitted:'))

    def test_can_print_xml(self):
        out = run_client(['bkr', 'job-clone','--xml', self.job.t_id])
        self.assert_('Submitted:' in out)
        self.assert_(self.job.to_xml(True,True).toxml() in out)

    def test_can_print_prettyxml(self):
        out = run_client(['bkr', 'job-clone','--prettyxml', self.job.t_id])
        self.assert_('Submitted:' in out)
        self.assert_(self.job.to_xml(True,True).toprettyxml() in out)

    def test_can_dryrun(self):
        out = run_client(['bkr', 'job-clone','--dryrun', self.job.t_id])
        self.assert_('Submitted:' not in out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-clone', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)
