import requests
from bkr.server.model import session, SystemAccessPolicy, SystemPermission, \
        Group
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest.server.requests_utils import put_json, post_json

class SystemPoolAccessPolicyHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by the access policy widget.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.pool = data_setup.create_system_pool(owning_user=self.owner)
            self.user = data_setup.create_user()
            self.pool.access_policy.add_rule(user=self.user,
                                             permission=SystemPermission.edit_system)

    def test_get_access_policy(self):
        response = requests.get(get_server_base() +
                'pools/%s/access-policy' % self.pool.name)
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['id'], self.pool.access_policy.id)
        self.assertEquals([p['value'] for p in json['possible_permissions']],
                ['view', 'view_power', 'edit_policy', 'edit_system',
                 'loan_any', 'loan_self', 'control_system', 'reserve'])
        self.assertItemsEqual(json['rules'], [
            {'id': self.pool.access_policy.rules[0].id, 'permission': 'view',
             'everybody': True, 'user': None, 'group': None},
            {'id': self.pool.access_policy.rules[1].id, 'permission': 'edit_system',
             'everybody': False, 'user': self.user.user_name, 'group': None,}
            ])

    def test_get_access_policy_for_nonexistent_pool(self):
        response = requests.get(get_server_base() + 'pools/notexist/access-policy')
        self.assertEquals(response.status_code, 404)

    def test_anonymous_cannot_add_delete_policy_rule(self):
        # attempt to add
        response = post_json(get_server_base() +
                            'pools/%s/access-policy/rules/' % self.pool.name,
                            data={'rule': []})
        self.assertEquals(response.status_code, 401)
        # attempt to remove
        response = requests.delete(get_server_base() + 'systems/%s/access-policy/rules/' % self.pool.name)
        self.assertEquals(response.status_code, 401)

    def test_unprivileged_user_cannot_add_remove_policy_rule(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        # attempt to add
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': user.user_name,
                                                  'password': 'password'}).raise_for_status()
        response = post_json(get_server_base() +
                             'pools/%s/access-policy/rules/' % self.pool.name,
                             session=s,
                             data={'rule': {} })
        self.assertEquals(response.status_code, 403)
        # attempt to remove
        response = s.delete(get_server_base() +
                            'pools/%s/access-policy/rules/' % self.pool.name)
        self.assertEquals(response.status_code, 403)

    def test_add_policy_rule(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                                                  'password': 'theowner'}).raise_for_status()
        response = post_json(get_server_base() +
                             'pools/%s/access-policy/rules/' % self.pool.name, session=s,
                             data={'permission': 'control_system',
                                   'everybody': True,
                                   'user': None,
                                   'group': None},
                                   )
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.pool.access_policy.rules[-1].permission,
                              SystemPermission.control_system)
            self.assertEquals(self.pool.access_policy.rules[-1].everybody, True)

    def test_delete_policy_rule(self):
        with session.begin():
            user = data_setup.create_user()
            self.pool.access_policy.add_rule(user=user,
                                             permission=SystemPermission.edit_system)
        self.assertTrue(self.pool.access_policy.grants
                        (user, SystemPermission.edit_system))
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                                                  'password': 'theowner'}).raise_for_status()
        response = s.delete(get_server_base() +
                            'pools/%s/access-policy/rules/'
                            '?user=%s'
                            '&permission=edit_system' % (self.pool.name, user.user_name))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertFalse(self.pool.access_policy.grants
                             (user, SystemPermission.edit_system))


