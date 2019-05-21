
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, create_client_config, \
        ClientTestCase

class UserModifyTest(ClientTestCase):

    def test_add_invalid_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        client_config = create_client_config(username=user.user_name,
            password='password')
        try:
            out = run_client(['bkr', 'user-modify', '--add-submission-delegate',
                '1thatdoesnotexist'], config=client_config)
            self.fail('Added an invalid submission delegate')
        except ClientError as e:
            self.assertTrue('1thatdoesnotexist is not a valid user' in \
                e.stderr_output, e.stderr_output)

    def test_add_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            delegate = data_setup.create_user()
        client_config = create_client_config(username=user.user_name,
            password='password')
        out = run_client(['bkr', 'user-modify', '--add-submission-delegate',
            delegate.user_name], config=client_config)
        self.assertTrue('Added submission delegate %s' % delegate.user_name in out, out)
        session.expire(user)
        with session.begin():
            self.assertEqual(user.submission_delegates, [delegate])

    def test_remove_invalid_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            notadelegate = data_setup.create_user()
        client_config = create_client_config(username=user.user_name,
            password='password')
        try:
            run_client(['bkr', 'user-modify', '--remove-submission-delegate',
                notadelegate.user_name], config=client_config)
            self.fail('Does not throw error when removing non delegate')
        except ClientError as e:
            self.assertTrue('%s is not a submission delegate of %s' % \
                (notadelegate.user_name, user) in e.stderr_output,
                e.stderr_output)

    def test_remove_submission_delegate(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            delegate1 = data_setup.create_user()
            delegate2 = data_setup.create_user()
            user.submission_delegates[:] = [delegate1, delegate2]
        client_config = create_client_config(username=user.user_name,
            password='password')
        out = run_client(['bkr', 'user-modify', '--remove-submission-delegate',
            delegate1.user_name], config=client_config)
        self.assertTrue('Removed submission delegate %s' % delegate1.user_name in out)
        session.expire(user)
        with session.begin():
            self.assertEqual(user.submission_delegates, [delegate2])
