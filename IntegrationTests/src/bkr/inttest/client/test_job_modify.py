import unittest
from turbogears.database import session
from bkr.inttest import with_transaction, data_setup
from bkr.inttest.client import run_client, create_client_config
from bkr.server.model import TaskBase

class JobModifyTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        user = data_setup.create_user(password='password')
        self.job = data_setup.create_job(owner=user)
        self.job_for_rs = data_setup.create_job(owner=user)
        self.client_config = create_client_config(username=user.user_name,
                                                  password='password')

    def test_ack_already_acked_job(self):
        # Is this lazy?
        self.test_ack_job()
        self.test_ack_job()

    def test_ack_job(self):
        out = run_client(['bkr', 'job-modify', self.job.t_id,  '--response', 'ack'])
        self.assert_(out == 'Successfully modified jobs %s\n' % self.job.t_id)
        j = TaskBase.get_by_t_id(self.job.t_id)
        for rs in j.recipesets:
            self.assert_('%s' % rs.nacked.response == 'ack')

    def test_nak_job(self):
        out = run_client(['bkr', 'job-modify', self.job.t_id,  '--response', 'nak'])
        self.assert_(out == 'Successfully modified jobs %s\n' % self.job.t_id)
        j = TaskBase.get_by_t_id(self.job.t_id)
        for rs in j.recipesets:
            self.assert_('%s' % rs.nacked.response == 'nak')

    def test_multiple_response_job(self):
        out = run_client(['bkr', 'job-modify', self.job.t_id, self.job_for_rs.t_id,  '--response', 'ack'])
        self.assert_(out == 'Successfully modified jobs %s %s\n' % (self.job.t_id, self.job_for_rs.t_id))
        j = TaskBase.get_by_t_id(self.job.t_id)
        for rs in j.recipesets:
            self.assert_('%s' % rs.nacked.response == 'ack')
        j2 = TaskBase.get_by_t_id(self.job_for_rs.t_id)
        for rs in j2.recipesets:
            self.assert_('%s' % rs.nacked.response == 'ack')

    def test_ack_rs(self):
        out = run_client(['bkr', 'job-modify', self.job.recipesets[0].t_id,  '--response', 'ack'])
        self.assert_(out == 'Successfully modified jobs %s\n' % self.job.recipesets[0].t_id)
        rs = TaskBase.get_by_t_id(self.job.recipesets[0].t_id)
        self.assert_('%s' % rs.nacked.response == 'ack')

    def test_nak_rs(self):
        out = run_client(['bkr', 'job-modify', self.job.recipesets[0].t_id,  '--response', 'nak'])
        self.assert_(out == 'Successfully modified jobs %s\n' % self.job.recipesets[0].t_id)
        rs = TaskBase.get_by_t_id(self.job.recipesets[0].t_id)
        self.assert_('%s' % rs.nacked.response == 'nak')

    def test_multiple_response_job(self):
        out = run_client(['bkr', 'job-modify', self.job.recipesets[0].t_id,
                          self.job_for_rs.recipesets[0].t_id,  '--response', 'ack'])
        self.assert_(out == 'Successfully modified jobs %s %s\n' %
            (self.job.recipesets[0].t_id, self.job_for_rs.recipesets[0].t_id))
        rs = TaskBase.get_by_t_id(self.job.recipesets[0].t_id)
        self.assert_('%s' % rs.nacked.response == 'ack')
        rs = TaskBase.get_by_t_id(self.job_for_rs.recipesets[0].t_id)
        self.assert_('%s' % rs.nacked.response == 'ack')

