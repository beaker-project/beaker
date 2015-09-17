# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase
from bkr.server.model import TaskStatus, Job, User
from bkr.server.tools import beakerd

class RemoveAccountTest(ClientTestCase):

    def test_admin_delete_self(self):
        try:
            run_client(['bkr', 'remove-account', 'admin'])
            self.fail('Must fail or die')
        except ClientError, e:
            self.assertIn('You cannot remove yourself', e.stderr_output)

    def test_delete_user(self):
        with session.begin():
            user1 = data_setup.create_user(password=u'asdf')
            user2 = data_setup.create_user(password=u'qwerty')

        run_client(['bkr', 'remove-account', user1.user_name, user2.user_name])
        with session.begin():
            session.refresh(user1)
            session.refresh(user2)
            self.assertTrue(user1.removed)
            self.assertTrue(user2.removed)
        try:
            run_client(['bkr', 'remove-account', user1.user_name])
            self.fail('Must fail or die')
        except ClientError, e:
            self.assertIn('User already removed', e.stderr_output)

    def test_non_admin_cannot_delete(self):
        with session.begin():
            user3 = data_setup.create_user(password=u'qwerty')
            client_config1 = create_client_config(username = user3.user_name,
                                                  password='qwerty')
        try:
            # it's okay to use the same user since we won't reach there anyway :-)
            run_client(['bkr', 'remove-account', user3.user_name],
                       config=client_config1)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assertIn('Not member of group: admin', e.stderr_output)

    def test_account_close_job_cancel(self):
        with session.begin():
            user1 = data_setup.create_user()
            job = data_setup.create_job(owner=user1)
            data_setup.mark_job_running(job)

        run_client(['bkr', 'remove-account', user1.user_name])

        # reflect the change in recipe task status when
        # update_dirty_jobs() is called
        session.expunge_all()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.by_id(job.id)
            self.assertEquals(job.status, TaskStatus.cancelled)
            self.assertIn('User %s removed' % user1.user_name,
                          job.recipesets[0].recipes[0].tasks[0].results[0].log)

    def test_close_account_transfer_ownership(self):
        with session.begin():
            new_owner = data_setup.create_user()
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user)

        run_client(['bkr', 'remove-account', '--new-owner=%s' % new_owner.user_name, user.user_name])

        with session.begin():
            session.expire_all()
            self.assertEqual(system.owner, new_owner)

    def test_invalid_newowner_errors(self):
        """If an invalid username is passed as a new owner, we expect the
        command to error without changing the system."""
        invalid_username = 'asdfasdfasdf'
        with session.begin():
            user = data_setup.create_user()
            data_setup.create_system()
            self.assertFalse(session.query(User).filter_by(user_name=invalid_username).count())

        try:
            run_client(['bkr', 'remove-account', '--new-owner=%s' % invalid_username, user.user_name])
            self.fail('Expected client to fail due to invalid new owner')
        except ClientError, e:
            self.assertIn('Invalid user name for owner', e.stderr_output)
