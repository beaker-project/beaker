
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from six import assertCountEqual, text_type
from sqlalchemy.orm.exc import NoResultFound
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as send_login, \
        patch_json, post_json, put_json
from bkr.server.database import session
from bkr.server.model import Activity, SystemPermission, SystemPool

class SystemPoolHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by the pool editing page.
    """
    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.system = data_setup.create_system(owner=self.owner, shared=False)
            self.pool = data_setup.create_system_pool(owning_user=self.owner)
            self.user = data_setup.create_user(password='password')
            self.group = data_setup.create_group()
            self.pool.systems[:] = [self.system]

    def test_create_system_pool(self):
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        data = {
            'name': 'newtest',
            'description': 'newtestdesciprtion',
        }
        response = post_json(get_server_base() + 'pools/', session=s, data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['name'], data['name'])
        self.assertEqual(response.json()['description'], data['description'])
        self.assertEqual(response.headers['Location'],
                get_server_base() + 'pools/newtest/')
        with session.begin():
            pool = SystemPool.by_name('newtest')
            self.assertEqual(pool.name, 'newtest')
            self.assertEqual(pool.description, 'newtestdesciprtion')
            self.assertEqual(pool.owner.user_name, self.owner.user_name)
            self.assertEqual(pool.access_policy.rules[0].everybody, True)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1498374
    def test_cannot_create_system_pool_owned_by_deleted_user(self):
        with session.begin():
            self.owner.removed = datetime.datetime.utcnow()
        s = requests.Session()
        send_login(s)
        response = post_json(get_server_base() + 'pools/', session=s,
                data={'name': 'asdf', 'owner': {'user_name': self.owner.user_name}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'System pool cannot be owned by deleted user %s' % self.owner.user_name)

    def test_get_system_pool(self):
        response = requests.get(get_server_base() +
                'pools/%s/' % self.pool.name, headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['id'], self.pool.id)
        self.assertEqual(json['name'], self.pool.name)
        self.assertEqual(json['description'], self.pool.description)

    def test_update_system_pool(self):
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = patch_json(get_server_base() +
                'pools/%s/' % self.pool.name, session=s,
                data={'name': 'newname',
                      'description': 'newdescription',
                      'owner': {'user_name': self.user.user_name}})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.pool.name, 'newname')
            self.assertEqual(self.pool.description, 'newdescription')
            self.assertEqual(self.pool.owner.user_name, self.user.user_name)

        s = requests.Session()
        send_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                              'pools/%s/' % self.pool.name, session=s,
                              data={'name': 'newname',
                                    'description': 'newdescription',
                                    'owner': {'group_name': self.group.group_name}})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.pool.owner, self.group)
            self.assertFalse(self.pool.owning_user)

    def test_cannot_update_system_pool_with_empty_name(self):
        """Verify that updating a system pool with an empty name returns an error."""
        self.assertTrue(self.pool.name, "Cannot run test with empty pool name in fixture")

        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = patch_json(get_server_base() + 'pools/%s/' % self.pool.name,
                              session=s,
                              data={'name': ''})
        self.assertEqual(400, response.status_code)
        self.assertEqual('Pool name cannot be empty', response.text)
        with session.begin():
            session.refresh(self.pool)
            self.assertTrue(self.pool.name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1498374
    def test_cannot_change_system_pool_owner_to_deleted_user(self):
        with session.begin():
            self.user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = patch_json(get_server_base() + 'pools/%s/' % self.pool.name,
                session=s, data={'owner': {'user_name': self.user.user_name}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'System pool cannot be owned by deleted user %s' % self.user.user_name)

    def test_add_system_to_pool(self):
        with session.begin():
            other_system = data_setup.create_system(owner=self.owner)
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = post_json(get_server_base() + 'pools/%s/systems/' % self.pool.name,
                session=s, data={'fqdn': other_system.fqdn})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            assertCountEqual(self, self.pool.systems, [self.system, other_system])
            self.assertEqual(self.pool.activity[-1].field_name, 'System')
            self.assertEqual(self.pool.activity[-1].action, 'Added')
            self.assertEqual(self.pool.activity[-1].new_value, text_type(other_system))
            self.assertEqual(other_system.activity[-1].field_name, 'Pool')
            self.assertEqual(other_system.activity[-1].action, 'Added')
            self.assertEqual(other_system.activity[-1].new_value, text_type(self.pool))

        # adding to a pool that doesn't exist is a 404
        response = post_json(get_server_base() + 'pools/nosuchpool/systems/',
                session=s, data={'fqdn': other_system.fqdn})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, 'System pool nosuchpool does not exist')

        # adding a system that doesn't exist is a 400
        response = post_json(get_server_base() + 'pools/%s/systems/' % self.pool.name,
                session=s, data={'fqdn': 'nosuchsystem'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "System 'nosuchsystem' does not exist")


    def test_remove_system_from_pool(self):
        with session.begin():
            system = data_setup.create_system(owner=self.owner)
            pool = data_setup.create_system_pool(systems=[system])
            pool.access_policy.add_rule(user=self.user,
                                        permission=SystemPermission.edit_system)
            system.active_access_policy = pool.access_policy

        self.assertIn(system, pool.systems)
        self.assertTrue(system.active_access_policy.grants
                        (self.user, SystemPermission.edit_system))

        s = requests.Session()

        # A system owner or a pool owner can remove a system from a pool
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = s.delete(get_server_base() + 'pools/%s/systems?fqdn=%s' % (pool.name, system.fqdn))
        response.raise_for_status()

        with session.begin():
            session.expire_all()
            self.assertNotIn(system, pool.systems)
            self.assertEqual(pool.activity[-1].field_name, 'System')
            self.assertEqual(pool.activity[-1].action, 'Removed')
            self.assertEqual(pool.activity[-1].old_value, text_type(system))
            self.assertEqual(system.activity[-2].field_name, 'Pool')
            self.assertEqual(system.activity[-2].action, 'Removed')
            self.assertEqual(system.activity[-2].old_value, text_type(pool))
            self.assertEqual(system.activity[-1].field_name, 'Active Access Policy')
            self.assertEqual(system.activity[-1].action, 'Changed')
            self.assertEqual(system.activity[-1].old_value, 'Pool policy: %s' % text_type(pool))
            self.assertEqual(system.activity[-1].new_value, 'Custom access policy')

        self.assertFalse(system.active_access_policy.grants
                         (self.user, SystemPermission.edit_system))

    def test_delete_system_pool(self):
        with session.begin():
            system = data_setup.create_system()
            random_user = data_setup.create_user(password='password')
            pool_owner = data_setup.create_user(password='password')
            pool_name = data_setup.unique_name('mypool%s')
            pool = data_setup.create_system_pool(name=pool_name,
                                                 owning_user=pool_owner,
                                                 systems=[system])
            pool.access_policy.add_rule(user=self.user,
                                        permission=SystemPermission.edit_system)
            system.active_access_policy = pool.access_policy

        unicode_pool = text_type(pool)
        self.assertIn(pool, system.pools)
        self.assertTrue(system.active_access_policy.grants
                        (self.user, SystemPermission.edit_system))
        # first as a random user
        s = requests.Session()
        send_login(s, user=random_user.user_name, password=u'password')
        response = s.delete(get_server_base() + 'pools/%s/' % pool_name)
        self.assertEqual(response.status_code, 403)

        # now as the pool owner
        s = requests.Session()
        send_login(s, user=pool_owner.user_name, password=u'password')
        response = s.delete(get_server_base() + 'pools/%s/' % pool_name)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            with self.assertRaises(NoResultFound):
                SystemPool.by_name(pool_name)

            self.assertNotIn(pool, system.pools)
            self.assertFalse(system.active_access_policy.grants
                             (self.user, SystemPermission.edit_system))

            self.assertEqual(system.activity[-1].field_name, 'Pool')
            self.assertEqual(system.activity[-1].action, 'Removed')
            self.assertEqual(system.activity[-1].old_value, unicode_pool)

            self.assertEqual(system.activity[-2].field_name, 'Active Access Policy')
            self.assertEqual(system.activity[-2].old_value, 'Pool policy: %s' % pool_name)
            self.assertEqual(system.activity[-2].new_value, 'Custom access policy')

            self.assertEqual(1, Activity.query
                              .filter(Activity.field_name == u'Pool')
                              .filter(Activity.action == u'Deleted')
                              .filter(Activity.old_value == pool_name).count(),
                              'Expected to find activity record for pool deletion')


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
        self.assertEqual(json['id'], self.pool.access_policy.id)
        self.assertEqual([p['value'] for p in json['possible_permissions']],
                ['view', 'view_power', 'edit_policy', 'edit_system',
                 'loan_any', 'loan_self', 'control_system', 'reserve'])
        assertCountEqual(self, json['rules'], [
            {'id': self.pool.access_policy.rules[0].id, 'permission': 'view',
             'everybody': True, 'user': None, 'group': None},
            {'id': self.pool.access_policy.rules[1].id, 'permission': 'edit_system',
             'everybody': False, 'user': self.user.user_name, 'group': None,}
            ])

    def test_get_access_policy_for_nonexistent_pool(self):
        response = requests.get(get_server_base() + 'pools/notexist/access-policy')
        self.assertEqual(response.status_code, 404)

    def test_save_access_policy(self):
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = put_json(get_server_base() +
                'pools/%s/access-policy/' % self.pool.name, session=s,
                data={'rules': [
                    # keep one existing rules, drop the other
                    {'id': self.pool.access_policy.rules[0].id, 'permission': 'view',
                     'everybody': True, 'user': None, 'group': None},
                    # .. and add a new rule
                    {'permission': 'control_system', 'everybody': True,
                     'user': None, 'group': None},
                ]})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.pool.access_policy.rules), 2)
            self.assertEqual(self.pool.access_policy.rules[0].permission,
                    SystemPermission.view)
            self.assertEqual(self.pool.access_policy.rules[1].permission,
                    SystemPermission.control_system)
            self.assertEqual(self.pool.access_policy.rules[1].everybody, True)

    def test_anonymous_cannot_add_delete_policy_rule(self):
        # attempt to add
        response = post_json(get_server_base() +
                            'pools/%s/access-policy/rules/' % self.pool.name,
                            data={'rule': []})
        self.assertEqual(response.status_code, 401)
        # attempt to remove
        response = requests.delete(get_server_base() + 'systems/%s/access-policy/rules/' % self.pool.name)
        self.assertEqual(response.status_code, 401)

    def test_unprivileged_user_cannot_add_remove_policy_rule(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        # attempt to add
        s = requests.Session()
        send_login(s, user=user.user_name, password=u'password')
        response = post_json(get_server_base() +
                             'pools/%s/access-policy/rules/' % self.pool.name,
                             session=s,
                             data={'rule': {} })
        self.assertEqual(response.status_code, 403)
        # attempt to remove
        response = s.delete(get_server_base() +
                            'pools/%s/access-policy/rules/' % self.pool.name)
        self.assertEqual(response.status_code, 403)

    def test_add_policy_rule(self):
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
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
            self.assertEqual(self.pool.access_policy.rules[-1].permission,
                              SystemPermission.control_system)
            self.assertEqual(self.pool.access_policy.rules[-1].everybody, True)

    def test_delete_policy_rule(self):
        with session.begin():
            user = data_setup.create_user()
            self.pool.access_policy.add_rule(user=user,
                                             permission=SystemPermission.edit_system)
        self.assertTrue(self.pool.access_policy.grants
                        (user, SystemPermission.edit_system))
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        response = s.delete(get_server_base() +
                            'pools/%s/access-policy/rules/'
                            '?user=%s'
                            '&permission=edit_system' % (self.pool.name, user.user_name))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertFalse(self.pool.access_policy.grants
                             (user, SystemPermission.edit_system))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_add_deleted_user_to_access_policy(self):
        with session.begin():
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
            bad_rule = {'user': deleted_user.user_name, 'permission': 'edit'}
        s = requests.Session()
        send_login(s, user=self.owner.user_name, password=u'theowner')
        # Two different APIs for manipulating access policy rules
        response = put_json(get_server_base() +
                'pools/%s/access-policy/' % self.pool.name, session=s,
                data={'rules': [bad_rule]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot add deleted user %s to access policy' % deleted_user.user_name)
        response = post_json(get_server_base() +
                'pools/%s/access-policy/rules/' % self.pool.name, session=s,
                data=bad_rule)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot add deleted user %s to access policy' % deleted_user.user_name)
