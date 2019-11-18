
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from unittest import SkipTest

from turbogears import config
from turbogears.database import session

from bkr.inttest import data_setup
from bkr.inttest.client import ClientError, ClientTestCase
from bkr.inttest.client import run_client, create_client_config


class UpdateOpenStackTrustTest(ClientTestCase):

    def setUp(self):
        if not config.get('openstack.identity_api_url'):
            raise SkipTest('OpenStack Integration is not enabled')
        with session.begin():
            self.password = u'asdf'
            self.user = data_setup.create_user(password=self.password)

            self.client_config = create_client_config(username=self.user.user_name,
                                                      password=self.password)

    def test_adds_openstack_trust_successfully(self):
        username = os.environ['OPENSTACK_DUMMY_USERNAME']
        password = os.environ['OPENSTACK_DUMMY_PASSWORD']
        project_name = os.environ['OPENSTACK_DUMMY_PROJECT_NAME']
        user_domain_name = os.environ.get('OPENSTACK_DUMMY_USER_DOMAIN_NAME')
        project_domain_name = os.environ.get('OPENSTACK_DUMMY_PROJECT_DOMAIN_NAME')

        if (user_domain_name and project_domain_name):
            run_client(['bkr', 'update-openstack-trust',
                        '--os-user-domain-name=%s' % user_domain_name,
                        '--os-username=%s' % username,
                        '--os-password=%s' % password,
                        '--os-project-domain-name=%s' % project_domain_name,
                        '--os-project-name=%s' % project_name],
                       config=self.client_config)
        else:
            run_client(['bkr', 'update-openstack-trust',
                        '--os-username=%s' % username,
                        '--os-password=%s' % password,
                        '--os-project-name=%s' % project_name],
                       config=self.client_config)

        with session.begin():
            session.refresh(self.user)
            self.assertIsNotNone(self.user.openstack_trust_id)

    def test_errors_if_unauthorised(self):
        try:
            run_client(['bkr', 'update-openstack-trust',
                        '--os-username=invalid',
                        '--os-password=invalid',
                        '--os-project-name=invalid-project'],
                       config=self.client_config)
            self.fail('should raise a ClientError')
        except ClientError as e:
            self.assertIn(
                    'Could not authenticate with OpenStack using your credentials',
                    e.stderr_output)

    def test_errors_if_unauthorised_with_domain_info(self):
        try:
            run_client(['bkr', 'update-openstack-trust',
                        '--os-user-domain-name=invalid',
                        '--os-username=invalid',
                        '--os-password=invalid',
                        '--os-project-domain-name=invalid',
                        '--os-project-name=beaker'],
                       config=self.client_config)
            self.fail('should raise a ClientError')
        except ClientError, e:
            self.assertIn(
                    'Could not authenticate with OpenStack using your credentials',
                    e.stderr_output)
