
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError, \
    create_client_config, ClientTestCase

class JobCancelTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_job()

    def test_can_cancel_group_job(self):
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
        out = run_client(['bkr', 'job-cancel',
            self.job.t_id], config=client_config)

    def test_cannot_cancel_recipe(self):
        try:
            run_client(['bkr', 'job-cancel',
                    self.job.recipesets[0].recipes[0].t_id])
            self.fail('should raise')
        except ClientError as e:
            self.assert_('Taskspec type must be one of'
                    in e.stderr_output, e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-cancel', '12345'])
            self.fail('should raise')
        except ClientError as e:
            self.assert_('Invalid taskspec' in e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=649608
    def test_cannot_cancel_other_peoples_job(self):
        with session.begin():
            user1 = data_setup.create_user(password='abc')
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner)

        try:
            run_client(['bkr', 'job-cancel', '--username', user1.user_name, '--password', 'abc', job.t_id])
            self.fail('should raise')
        except ClientError as e:
            self.assertEquals(e.status, 1)
            self.assert_('You don\'t have permission to cancel'
                    in e.stderr_output, e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=995012
    def test_record_job_cancel(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)

        run_client(['bkr', 'job-cancel', '--username', job_owner.user_name, '--password', 'owner', job.t_id])
        self.assertEquals(job.activity[0].action, u'Cancelled')
        self.assertEquals(job.activity[0].user, job_owner)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1124756
    def test_can_cancel_recipe_task(self):
        t_id = self.job.recipesets[0].recipes[0].tasks[0].t_id
        out = run_client(['bkr', 'job-cancel', t_id])
        self.assertEquals('Cancelled %s\n' % t_id, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173376
    def test_clear_rows_in_system_recipe_map(self):
        with session.begin():
            system = data_setup.create_system()
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_job(owner=job_owner)
            job.recipesets[0].recipes[0].systems[:] = [system]
        # check if rows in system_recipe_map
        self.assertNotEquals(len(job.recipesets[0].recipes[0].systems), 0)
        out = run_client(['bkr', 'job-cancel', '--username', job_owner.user_name, '--password', 'owner', job.t_id])
        self.assertEquals('Cancelled %s\n' % job.t_id, out)
        with session.begin():
            session.expire_all()
            # check if no rows in system_recipe_map
            self.assertEqual(len(job.recipesets[0].recipes[0].systems), 0)

    def test_add_msg_when_cancelling_running_job_successful(self):
        with session.begin():
            job_owner = data_setup.create_user(password=u'owner')
            job = data_setup.create_running_job(owner=job_owner)

        run_client(['bkr', 'job-cancel', job.t_id,
                    '--username', job_owner.user_name,
                    '--password', 'owner',
                    '--msg=test adding cancel message'])
        with session.begin():
            session.refresh(job)
            self.assertEquals(job.activity[0].action, u'Cancelled')
            self.assertEquals(job.recipesets[0].recipes[0].tasks[0].results[0].log,
                    'test adding cancel message')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1174615
    def test_cancel_with_invalid_ID_raise_error(self):
        try:
            run_client(['bkr', 'job-cancel', 'T:9q9999q'])
            self.fail('should raise')
        except ClientError as e:
            self.assertIn('Invalid T 9q9999q', e.stderr_output)