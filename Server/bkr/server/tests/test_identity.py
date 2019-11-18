# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from bkr.server import identity
from bkr.server.app import app
from bkr.server.model import session, User
from bkr.server.tests import data_setup


def acquire_cookie(user, proxied_by_user=None):
    # Fake prior successful authentication in order to get a valid cookie.
    with app.test_request_context():
        identity.set_authentication(user, proxied_by_user)
        return '%s=%s' % (identity._token_cookie_name, identity._generate_token())

class CheckAuthenticationUnitTest(unittest.TestCase):

    def setUp(self):
        session.begin()
        self.addCleanup(session.rollback)

    def test_obeys_REMOTE_USER(self):
        # REMOTE_USER will be set if Apache is configured to do external
        # authentication and the authentication was successful for this
        # request.
        user = data_setup.create_user()
        environ = {'REMOTE_USER': user.user_name}
        with app.test_request_context(environ_overrides=environ):
            identity.check_authentication()
            self.assertEqual(identity.current.user, user)
            self.assertIsNone(identity.current.proxied_by_user)

    def test_REMOTE_USER_is_ignored_if_user_does_not_exist(self):
        environ = {'REMOTE_USER': 'idontexist'}
        with app.test_request_context(environ_overrides=environ):
            identity.check_authentication()
            self.assertIsNone(identity.current.user)
            self.assertIsNone(identity.current.proxied_by_user)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1112925
    def test_user_is_created_if_REMOTE_USER_vars_are_populated(self):
        new_username = 'mwatney'
        new_user_display_name = 'Mark Watney'
        new_user_email = 'mwatney@nasa.gov'
        environ = {
            'REMOTE_USER': new_username,
            'REMOTE_USER_FULLNAME': new_user_display_name,
            'REMOTE_USER_EMAIL': new_user_email,
        }
        with app.test_request_context(environ_overrides=environ):
            identity.check_authentication()
            new_user = User.query.filter_by(user_name=new_username).one()
            self.assertEqual(identity.current.user, new_user)
            self.assertIsNone(identity.current.proxied_by_user)

    def test_obeys_token_in_cookie(self):
        user = data_setup.create_user()
        cookie = acquire_cookie(user)
        with app.test_request_context(headers={'Cookie': cookie}):
            identity.check_authentication()
            self.assertEqual(identity.current.user, user)
            self.assertIsNone(identity.current.proxied_by_user)

    def test_obeys_token_with_proxied_auth(self):
        user = data_setup.create_user()
        proxy = data_setup.create_user()
        cookie = acquire_cookie(user, proxy)
        with app.test_request_context(headers={'Cookie': cookie}):
            identity.check_authentication()
            self.assertEqual(identity.current.user, user)
            self.assertEqual(identity.current.proxied_by_user, proxy)

    def test_token_is_ignored_if_user_does_not_exist(self):
        # This should be impossible since we don't allow deleting User objects.
        # But let's test it for completeness' sake.
        user = data_setup.create_user()
        cookie = acquire_cookie(user)
        session.delete(user)
        session.flush()
        with app.test_request_context(headers={'Cookie': cookie}):
            identity.check_authentication()
            self.assertIsNone(identity.current.user)
            self.assertIsNone(identity.current.proxied_by_user)

    def test_token_is_ignored_if_proxy_does_not_exist(self):
        # As above, this should never actually happen.
        user = data_setup.create_user()
        proxy = data_setup.create_user()
        cookie = acquire_cookie(user, proxy)
        session.delete(proxy)
        session.flush()
        with app.test_request_context(headers={'Cookie': cookie}):
            identity.check_authentication()
            self.assertIsNone(identity.current.user)
            self.assertIsNone(identity.current.proxied_by_user)

    def test_REMOTE_USER_takes_precedence_over_cookie(self):
        # This could happen if the user somehow reauthenticates to Apache as
        # a different user but an existing session cookie is left behind
        # because they didn't log out of Beaker.
        old_user = data_setup.create_user()
        new_user = data_setup.create_user()
        cookie = acquire_cookie(old_user)
        environ = {'REMOTE_USER': new_user.user_name}
        with app.test_request_context(environ_overrides=environ,
                                      headers={'Cookie': cookie}):
            identity.check_authentication()
            self.assertEqual(identity.current.user, new_user)

    def test_authentication_is_ignored_if_user_is_disabled(self):
        user = data_setup.create_user()
        cookie = acquire_cookie(user)
        environ = {'REMOTE_USER': user.user_name}
        user.disabled = True
        with app.test_request_context(environ_overrides=environ,
                                      headers={'Cookie': cookie}):
            identity.check_authentication()
            self.assertIsNone(identity.current.user)
            self.assertIsNone(identity.current.proxied_by_user)
