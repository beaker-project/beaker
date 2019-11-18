# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import tempfile
from unittest import SkipTest
from bkr.server.model import session, Permission
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.client import run_client, create_client_config, ClientError, ClientTestCase


class WhoAmITest(ClientTestCase):

    def test_whoami(self):
        out = run_client(['bkr', 'whoami'])
        self.assertIn(data_setup.ADMIN_USER, out)

    def test_whoami_proxy_user(self):
        with session.begin():
            group = data_setup.create_group()
            proxy_perm = Permission.by_name(u'proxy_auth')
            group.permissions.append(proxy_perm)
            proxied_user = data_setup.create_user()
            proxying_user = data_setup.create_user(password='password')
            group.add_member(proxying_user)
        out = run_client(['bkr', 'whoami',
                          '--proxy-user', proxied_user.user_name],
                         config=create_client_config(
                             username=proxying_user.user_name,
                             password='password'))
        self.assertIn('"username": "%s"' % proxied_user.user_name, out)
        self.assertIn('"proxied_by_username": "%s"' % proxying_user.user_name, out)

    def test_wrong_password(self):
        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'whoami'],
                       config=create_client_config(password='gotofail'))
        self.assertIn('Invalid username or password', assertion.exception.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1072127
    def test_password_not_set_on_server_side(self):
        # A user account might have a NULL password if the Beaker site is using
        # Kerberos authentication, or if their account is new and the admin
        # hasn't set a password yet.
        with session.begin():
            user = data_setup.create_user(password=None)
        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'whoami'], config=create_client_config(
                username=user.user_name, password='irrelevant'))
        self.assertIn('Invalid username or password', assertion.exception.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1350959
    def test_error_message_if_cacert_points_to_wrong_path(self):
        config = create_client_config(cacert='/does/not/exist')

        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'whoami'], config=config)
        self.assertEqual(
            'CA_CERT configuration points to non-existing file: /does/not/exist\n',
            assertion.exception.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=844364
    def test_config_is_read_from_user_config_and_system_config(self):
        # We tell the client to use a config which lacks HUB_URL. The correct
        # HUB_URL setting will be inherited from the system-wide config instead
        # and so the command still succeeds.
        if not os.path.exists('/etc/beaker/client.conf'):
            raise SkipTest('System-wide client config does not exist')
        required_setting = 'HUB_URL = "%s"' % get_server_base().rstrip('/')
        if required_setting not in open('/etc/beaker/client.conf').read().splitlines():
            raise SkipTest('System-wide client config is not pointing at the expected server')
        with session.begin():
            user = data_setup.create_user(password=u'password')
        config = tempfile.NamedTemporaryFile(prefix='bkr-inttest-client-conf-')
        config.write('\n'.join([
            # omit HUB_URL
            'AUTH_METHOD = "password"',
            'USERNAME = "%s"' % user.user_name,
            'PASSWORD = "password"',
        ]))
        config.flush()
        out = run_client(['bkr', 'whoami'], config=config)
        self.assertIn(user.user_name, out)
