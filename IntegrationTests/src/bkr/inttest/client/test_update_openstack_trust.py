
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from turbogears.database import session
from turbogears import config
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, create_client_config
from bkr.inttest.client import ClientError, ClientTestCase
from unittest2 import SkipTest


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
        project = os.environ['OPENSTACK_DUMMY_PROJECT_NAME']

        run_client(['bkr', 'update-openstack-trust',
                    '--os-username=%s' % username,
                    '--os-password=%s' % password,
                    '--os-project-name=%s' % project],
                   config=self.client_config)

        with session.begin():
            session.refresh(self.user)
            self.assertIsNotNone(self.user.openstack_trust_id)
