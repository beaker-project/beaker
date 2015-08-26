
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase
import json

class JobListTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        jobs_to_generate = 2;
        self.products = [data_setup.create_product() for product in range(jobs_to_generate)]
        self.users = [data_setup.create_user(password='mypass') for user in range(jobs_to_generate)]
        self.jobs = [data_setup.create_completed_job(product=self.products[x], owner=self.users[x]) for x in range(jobs_to_generate)]
        self.client_configs = [create_client_config(username=user.user_name, password='mypass') for user in self.users]

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
        out = run_client(['bkr', 'job-list', '--owner', self.users[0].user_name, '--min-id', \
                              '{0}'.format(self.jobs[0].id), '--max-id', '{0}'.format(self.jobs[0].id)])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out)

    def test_list_jobs_by_whiteboard(self):
        out = run_client(['bkr', 'job-list', '--whiteboard', self.jobs[0].whiteboard])
        self.assert_(self.jobs[0].t_id in out, out)
        out = run_client(['bkr', 'job-list', '--whiteboard', 'foobar'])
        self.assert_(self.jobs[0].t_id not in out, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1229938
    def test_list_jobs_by_retention_tag(self):
        with session.begin():
            job_tagged_scratch = data_setup.create_completed_job(
                    retention_tag=u'scratch')
            job_tagged_audit = data_setup.create_completed_job(
                    retention_tag=u'audit', product=data_setup.create_product())
        out = run_client(['bkr', 'job-list', '--format=json', '--tag=audit'])
        joblist = json.loads(out)
        self.assertIn(job_tagged_audit.t_id, joblist)
        self.assertNotIn(job_tagged_scratch.t_id, joblist)
        out = run_client(['bkr', 'job-list', '--format=json', '--tag=scratch'])
        joblist = json.loads(out)
        self.assertIn(job_tagged_scratch.t_id, joblist)
        self.assertNotIn(job_tagged_audit.t_id, joblist)

    #https://bugzilla.redhat.com/show_bug.cgi?id=816490
    def test_list_jobs_by_jid(self):
        out = run_client(['bkr', 'job-list', '--min-id', '{0}'.format(self.jobs[1].id)])
        self.assert_(self.jobs[1].t_id in out and self.jobs[0].t_id not in out)

        out = run_client(['bkr', 'job-list', '--max-id', '{0}'.format(self.jobs[0].id)])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out)

    #https://bugzilla.redhat.com/show_bug.cgi?id=907650
    def test_list_jobs_mine(self):
        out = run_client(['bkr', 'job-list', '--mine'], config=self.client_configs[0])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out, out)
        out = run_client(['bkr', 'job-list', '--mine',
                          '--format','json'],
                         config=self.client_configs[0])
        out = json.loads(out)
        self.assertIn(self.jobs[0].t_id, out)
        self.assertNotIn(self.jobs[1].t_id, out)
        self.assertRaises(ClientError, run_client, ['bkr', 'job-list', '--mine', \
                                                        '--username', 'xyz',\
                                                        '--password','xyz'])
