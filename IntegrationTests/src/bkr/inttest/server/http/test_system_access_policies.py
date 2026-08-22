
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from six import assertCountEqual
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as requests_login, \
        post_json, put_json
from bkr.server.database import session
from bkr.server.model import SystemPermission

class SystemAccessPolicyHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by the access policy widget.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.system = data_setup.create_system(owner=self.owner, shared=False)
            self.policy = self.system.custom_access_policy
            self.policy.add_rule(everybody=True, permission=SystemPermission.reserve)
            self.privileged_group = data_setup.create_group()
            self.policy.add_rule(group=self.privileged_group,
                    permission=SystemPermission.edit_system)

    def test_get_custom_access_policy(self):
        response = requests.get(get_server_base() +
                'systems/%s/access-policy' % self.system.fqdn)
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['id'], self.policy.id)
        self.assertEqual([p['value'] for p in json['possible_permissions']],
                ['view', 'view_power', 'edit_policy', 'edit_system',
                 'loan_any', 'loan_self', 'control_system', 'reserve'])
        assertCountEqual(self, json['rules'], [
            {'id': self.policy.rules[0].id, 'permission': 'view',
             'everybody': True, 'user': None, 'group': None},
            {'id': self.policy.rules[1].id, 'permission': 'reserve',
             'everybody': True, 'user': None, 'group': None},
            {'id': self.policy.rules[2].id, 'permission': 'edit_system',
             'everybody': False, 'user': None,
             'group': self.privileged_group.group_name},
        ])

    def test_get_access_policy_for_nonexistent_system(self):
        response = requests.get(get_server_base() + 'systems/notexist/access-policy')
        self.assertEqual(response.status_code, 404)

    def test_mine_filter_needs_authentication(self):
        response = requests.get(get_server_base() +
                'systems/%s/access-policy?mine=1' % self.system.fqdn)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.text,
                "The 'mine' access policy filter requires authentication")

    def test_anonymous_cannot_save_policy(self):
        response = put_json(get_server_base() +
                'systems/%s/access-policy' % self.system.fqdn,
                data={'rules': []})
        self.assertEqual(response.status_code, 401)

    def test_unprivileged_user_cannot_save_policy(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = put_json(get_server_base() +
                'systems/%s/access-policy' % self.system.fqdn,
                session=s, data={'rules': []})
        self.assertEqual(response.status_code, 403)

    def test_save_policy(self):
        with session.begin():
            other_user = data_setup.create_user()
            other_group = data_setup.create_group()
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        response = put_json(get_server_base() +
                'systems/%s/access-policy' % self.system.fqdn, session=s,
                data={'rules': [
                    # keep two existing rules, drop the other
                    {'id': self.policy.rules[0].id, 'permission': 'view',
                     'everybody': True, 'user': None, 'group': None},
                    {'id': self.policy.rules[2].id, 'permission': 'edit_system',
                     'user': None, 'group': self.privileged_group.group_name},
                    # .. and two new rules
                    {'permission': 'control_system', 'everybody': False,
                     'user': None, 'group': other_group.group_name},
                    {'permission': 'reserve', 'everybody': False,
                     'user': other_user.user_name, 'group': None},
                ]})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.policy.rules), 4)
            self.assertEqual(self.policy.rules[0].permission,
                    SystemPermission.view)
            self.assertEqual(self.policy.rules[0].everybody, True)
            self.assertEqual(self.policy.rules[1].permission,
                    SystemPermission.edit_system)
            self.assertEqual(self.policy.rules[1].group, self.privileged_group)
            self.assertEqual(self.policy.rules[2].permission,
                    SystemPermission.control_system)
            self.assertEqual(self.policy.rules[2].group, other_group)
            self.assertEqual(self.policy.rules[3].permission,
                    SystemPermission.reserve)
            self.assertEqual(self.policy.rules[3].user, other_user)
            self.assertEqual(self.system.activity[0].action, u'Added')
            self.assertEqual(self.system.activity[0].field_name, u'Access Policy Rule')
            self.assertEqual(self.system.activity[0].new_value,
                    u'User:%s:reserve' % other_user.user_name)
            self.assertEqual(self.system.activity[1].action, u'Added')
            self.assertEqual(self.system.activity[1].field_name, u'Access Policy Rule')
            self.assertEqual(self.system.activity[1].new_value,
                    u'Group:%s:control_system' % other_group.group_name)
            self.assertEqual(self.system.activity[2].action, u'Removed')
            self.assertEqual(self.system.activity[2].field_name, u'Access Policy Rule')
            self.assertEqual(self.system.activity[2].old_value, u'Everybody::reserve')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_add_deleted_user_to_access_policy(self):
        with session.begin():
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
            bad_rule = {'user': deleted_user.user_name, 'permission': 'edit'}
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'theowner')
        # Two different APIs for manipulating access policy rules
        response = put_json(get_server_base() +
                'systems/%s/access-policy' % self.system.fqdn, session=s,
                data={'rules': [bad_rule]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot add deleted user %s to access policy' % deleted_user.user_name)
        response = post_json(get_server_base() +
                'systems/%s/access-policy/rules/' % self.system.fqdn, session=s,
                data=bad_rule)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot add deleted user %s to access policy' % deleted_user.user_name)

    def test_get_active_access_policy(self):
        response = requests.get(get_server_base() +
                'systems/%s/active-access-policy/' % self.system.fqdn)
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['id'], self.policy.id)
        self.assertEqual([p['value'] for p in json['possible_permissions']],
                ['view', 'view_power', 'edit_policy', 'edit_system',
                 'loan_any', 'loan_self', 'control_system', 'reserve'])
        assertCountEqual(self, json['rules'], [
            {'id': self.policy.rules[0].id, 'permission': 'view',
             'everybody': True, 'user': None, 'group': None},
            {'id': self.policy.rules[1].id, 'permission': 'reserve',
             'everybody': True, 'user': None, 'group': None},
            {'id': self.policy.rules[2].id, 'permission': 'edit_system',
             'everybody': False, 'user': None,
             'group': self.privileged_group.group_name},
        ])
