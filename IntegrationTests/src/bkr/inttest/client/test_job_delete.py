
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
    ClientTestCase

class JobDeleteTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.user = data_setup.create_user(password=u'asdf')
        self.job = data_setup.create_completed_job(owner=self.user)
        self.client_config = create_client_config(username=self.user.user_name,
                password='asdf')

    def test_delete_group_job(self):
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user(password='password')
            user2 = data_setup.create_user()
            group.add_member(user)
            group.add_member(user2)
            self.job.group = group
            self.job.owner = user2
        client_config = create_client_config(username=user.user_name,
            password='password')
        out = run_client(['bkr', 'job-delete', self.job.t_id],
                config=client_config)
        self.assert_(out.startswith('Jobs deleted:'), out)
        self.assert_(self.job.t_id in out, out)

    def test_delete_job(self):
        out = run_client(['bkr', 'job-delete', self.job.t_id],
                config=self.client_config)
        self.assert_(out.startswith('Jobs deleted:'), out)
        self.assert_(self.job.t_id in out, out)

    def test_delete_others_job(self):
        with session.begin():
            other_user = data_setup.create_user(password=u'asdf')
            other_job = data_setup.create_completed_job(owner=other_user)
        try:
            out = run_client(['bkr', 'job-delete', other_job.t_id],
                             config=self.client_config)
            self.fail('should raise')
        except ClientError as e:
            self.assert_("don't have permission" in e.stderr_output)

    def test_cant_delete_group_mates_job(self):
        # The test_delete_group_job case above is similar, but here the job is
        # *not* declared as a group job, therefore we don't have permission to
        # delete it.
        with session.begin():
            group = data_setup.create_group()
            mate = data_setup.create_user(password=u'asdf')
            test_job = data_setup.create_completed_job(owner=mate)
            group.add_member(self.user)
            group.add_member(mate)
        try:
            run_client(['bkr', 'job-delete', test_job.t_id],
                config=self.client_config)
            self.fail('We should not have permission to delete %s' % \
                test_job.t_id)
        except ClientError as e:
            self.assertIn("You don't have permission to delete job %s" %
            test_job.t_id, e.stderr_output)

    def test_delete_job_with_admin(self):
        with session.begin():
            other_user = data_setup.create_user(password=u'asdf')
            tag = data_setup.create_retention_tag(name=u'myblahtag')
            job1 = data_setup.create_completed_job(owner=other_user)
            job2 = data_setup.create_completed_job(owner=other_user,
                                                   retention_tag=tag.tag)

        # As the default admin user
        # Admin can delete other's job with job ID
        out = run_client(['bkr', 'job-delete', job1.t_id])
        self.assert_(out.startswith('Jobs deleted:'), out)
        self.assert_(job1.t_id in out, out)

        # Admin can not delete other's job with tags
        out = run_client(['bkr', 'job-delete', '-t%s' % tag.tag])
        self.assert_(out.startswith('Jobs deleted:'), out)
        self.assert_(job2.t_id not in out, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-delete', '12345'])
            self.fail('should raise')
        except ClientError as e:
            self.assert_('Invalid taskspec' in e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=990943
    def test_zero_value_completeDays(self):
        try:
            run_client(['bkr', 'job-delete', '--completeDays', '0'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('Please pass a positive integer to completeDays', e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=990943
    def test_negative_value_completeDays(self):
        try:
            run_client(['bkr', 'job-delete', '--completeDays', '-1'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('Please pass a positive integer to completeDays', e.stderr_output)
