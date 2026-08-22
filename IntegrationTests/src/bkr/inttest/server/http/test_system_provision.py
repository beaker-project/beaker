# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest as unittest
import requests
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.requests_utils import login as requests_login, post_json
from bkr.server.database import session
from bkr.server.model import SystemPermission


class SystemProvisionHTTPTest(unittest.TestCase):

    def setUp(self):
        self.system = data_setup.create_system(shared=True)
        self.system.custom_access_policy.add_rule(everybody=True,
                                                  permission=SystemPermission.control_system)

    def test_no_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = post_json(get_server_base() +
                             'systems/%s/installations/' % self.system.fqdn,
                             session=s, data={'distro_tree': {'id': -1}})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.text,
                          'Insufficient permissions: Cannot provision system')
