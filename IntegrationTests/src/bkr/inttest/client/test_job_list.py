
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase
import json
from bkr.server.model import TaskStatus

class JobListTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        jobs_to_generate = 2
        self.products = [data_setup.create_product() for _ in range(jobs_to_generate)]
        self.users = [data_setup.create_user(password='mypass') for _ in range(jobs_to_generate)]
        self.groups = [data_setup.create_group() for _ in range(jobs_to_generate)]
        _ = [group.add_member(self.users[i]) for i, group in enumerate(self.groups)]

        self.jobs = [data_setup.create_completed_job(product=self.products[x],
                                                     owner=self.users[x],
                                                     group=self.groups[x])
                     for x in range(jobs_to_generate)]
        self.client_configs = [create_client_config(username=user.user_name, password='mypass') for user in self.users]

    def test_list_jobs_by_product(self):
        out = run_client(['bkr', 'job-list', '--product', self.products[0].name])
        self.assert_(self.jobs[0].t_id in out, [self.jobs[0].t_id, out])
        self.assertRaises(ClientError, run_client, ['bkr', 'job-list', '--product', 'foobar'])

    def test_list_jobs_by_owner(self):
        out = run_client(['bkr', 'job-list', '--owner', self.users[0].user_name])
        self.assert_(self.jobs[0].t_id in out, out)

        out = run_client(['bkr', 'job-list', '--owner', self.users[0].user_name, '--limit', '1'])
        self.assert_(len(json.loads(out)) == 1, out)

        with self.assertRaisesRegexp(ClientError, 'Owner.*is invalid'):
            run_client(['bkr', 'job-list', '--owner', 'foobar'])

        out = run_client(['bkr', 'job-list', '--owner', self.users[0].user_name, '--min-id',
                          '{0}'.format(self.jobs[0].id), '--max-id', '{0}'.format(self.jobs[0].id)])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out)

    def test_list_jobs_by_whiteboard(self):
        out = run_client(['bkr', 'job-list', '--whiteboard', self.jobs[0].whiteboard])
        self.assert_(self.jobs[0].t_id in out, out)
        out = run_client(['bkr', 'job-list', '--whiteboard', 'foobar'])
        self.assert_(self.jobs[0].t_id not in out, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1277340
    def test_list_jobs_by_whiteboard_substring(self):
        with session.begin():
            included_job = data_setup.create_completed_job(whiteboard=u'Prince of Penzance')
            excluded_job = data_setup.create_completed_job(whiteboard=u'Princess of Persia')
        out = run_client(['bkr', 'job-list', '--format=list', '--whiteboard=penzance'])
        listed_job_ids = out.splitlines()
        self.assertIn(included_job.t_id, listed_job_ids)
        self.assertNotIn(excluded_job.t_id, listed_job_ids)
        # This was accidental undocumented functionality supported by the
        # original implementation of jobs.filter. Some people are probably
        # relying on it.
        out = run_client(['bkr', 'job-list', '--format=list', '--whiteboard=p%z_nce'])
        listed_job_ids = out.splitlines()
        self.assertIn(included_job.t_id, listed_job_ids)
        self.assertNotIn(excluded_job.t_id, listed_job_ids)

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
        self.assertRaises(ClientError, run_client, ['bkr', 'job-list', '--mine',
                                                    '--username', 'xyz',
                                                    '--password','xyz'])

    def test_list_jobs_my_groups(self):
        out = run_client(['bkr', 'job-list', '--my-groups'], config=self.client_configs[0])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out, out)

        out = run_client(['bkr', 'job-list', '--my-groups'], config=self.client_configs[1])
        self.assert_(self.jobs[1].t_id in out and self.jobs[0].t_id not in out, out)

        out = run_client(['bkr', 'job-list', '--my-groups', '--format','json'],
                         config=self.client_configs[0])
        out = json.loads(out)
        self.assertIn(self.jobs[0].t_id, out)
        self.assertNotIn(self.jobs[1].t_id, out)

        self.assertRaises(ClientError, run_client, ['bkr', 'job-list', '--my-groups',
                                                    '--username', 'xyz',
                                                    '--password','xyz'])

    def test_list_jobs_by_group(self):
        out = run_client(['bkr', 'job-list', '--group', self.groups[0].group_name])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out, out)

        out = run_client(['bkr', 'job-list', '--group', self.groups[1].group_name])
        self.assert_(self.jobs[1].t_id in out and self.jobs[0].t_id not in out, out)

        out = run_client(['bkr', 'job-list', '--group', self.groups[1].group_name, '--limit', '1'])
        self.assert_(len(json.loads(out)) == 1, out)

        with self.assertRaisesRegexp(ClientError, 'No such group \'foobar\''):
            run_client(['bkr', 'job-list', '--group', 'foobar'])

        out = run_client(['bkr', 'job-list', '--group',
                          self.groups[0].group_name,
                          '--min-id', '{0}'.format(self.jobs[0].id), '--max-id', '{0}'.format(self.jobs[0].id)])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id not in out)

    def test_list_jobs_both_by_mine_and_owner(self):
        out = run_client(['bkr', 'job-list', '--mine', '--owner', self.users[1].user_name], config=self.client_configs[0])
        self.assert_(self.jobs[0].t_id in out and self.jobs[1].t_id in out, out)

    def test_cannot_specify_finished_and_unfinished_at_the_same_time (self):
        try:
            run_client(['bkr', 'job-list', '--finished', '--unfinished'])
            self.fail('should raise')
        except ClientError as e:
            self.assertEqual(e.status, 2)
            self.assertIn("Only one of --finished or --unfinished may be specified", e.stderr_output)

    def test_filter_finished_jobs(self):
        with session.begin():
            completed_job = data_setup.create_completed_job(task_status=TaskStatus.completed)
            cancelled_job = data_setup.create_completed_job(task_status=TaskStatus.cancelled)
            aborted_job = data_setup.create_completed_job(task_status=TaskStatus.aborted)
            running_job = data_setup.create_running_job()
        out = run_client(['bkr', 'job-list', '--finished'])
        self.assertIn(completed_job.t_id, out)
        self.assertIn(cancelled_job.t_id, out)
        self.assertIn(aborted_job.t_id, out)
        self.assertNotIn(running_job.t_id, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1175853
    def test_filter_unfinished_jobs(self):
        with session.begin():
            queued_job = data_setup.create_queued_job()
            running_job = data_setup.create_running_job()
            waiting_job = data_setup.create_waiting_job()
            scheduled_job = data_setup.create_scheduled_job()
            installing_job = data_setup.create_installing_job()
            completed_job = data_setup.create_completed_job()
        out = run_client(['bkr', 'job-list', '--unfinished'])
        self.assertIn(queued_job.t_id, out)
        self.assertIn(running_job.t_id, out)
        self.assertIn(waiting_job.t_id, out)
        self.assertIn(scheduled_job.t_id, out)
        self.assertIn(installing_job.t_id, out)
        self.assertNotIn(completed_job.t_id, out)