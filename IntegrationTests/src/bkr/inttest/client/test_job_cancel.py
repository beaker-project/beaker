
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError, \
    create_client_config

class JobCancelTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_job()

    def test_can_cancel_group_job(self):
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user(password='password')
            user2 = data_setup.create_user()
            user.groups.append(group)
            user2.groups.append(group)
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
        except ClientError, e:
            self.assertEquals(e.status, 1)
            self.assert_('Task type R is not stoppable'
                    in e.stderr_output, e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-cancel', '12345'])
            fail('should raise')
        except ClientError, e:
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
        except ClientError, e:
            self.assertEquals(e.status, 1)
            self.assert_('You don\'t have permission to cancel'
                    in e.stderr_output, e.stderr_output)

