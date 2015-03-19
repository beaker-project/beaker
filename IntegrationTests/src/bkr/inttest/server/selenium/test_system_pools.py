import requests
from bkr.server.model import session, SystemAccessPolicy, SystemPermission, \
        Group, SystemPool, User, Activity
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, check_pool_search_results
from bkr.inttest.server.requests_utils import put_json, post_json, patch_json
from sqlalchemy.orm.exc import NoResultFound

class SystemPoolsGridTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_searching_by_name(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            other_pool = data_setup.create_system_pool()
        b = self.browser
        b.get(get_server_base() + 'pools/')
        b.find_element_by_class_name('search-query').send_keys(
                'name:"%s"' % pool.name)
        b.find_element_by_class_name('grid-filter').submit()
        check_pool_search_results(b, present=[pool], absent=[other_pool])

    def test_create_button_is_absent_when_not_logged_in(self):
        b = self.browser
        b.get(get_server_base() + 'pools/')
        b.find_element_by_xpath('//div[@id="grid" and '
                'not(.//button[normalize-space(string(.))="Create"])]')

    def test_create_pool(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'pools/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]')\
            .click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('name').send_keys('inflatable')
        modal.find_element_by_tag_name('form').submit()
        import time; time.sleep(5) # XXX replace when pool page is implemented
        with session.begin():
            pool = SystemPool.by_name(u'inflatable')
            self.assertEquals(pool.owner, User.by_user_name(data_setup.ADMIN_USER))

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
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                                                  'password': 'theowner'}).raise_for_status()
        data = {
            'name': 'newtest',
            'description': 'newtestdesciprtion',
        }
        response = post_json(get_server_base() + 'pools/', session=s, data=data)
        self.assertEquals(response.status_code, 201)
        self.assertEquals(response.json()['name'], data['name'])
        self.assertEquals(response.json()['description'], data['description'])
        self.assertEquals(response.headers['Location'],
                get_server_base() + 'pools/newtest/')
        with session.begin():
            pool = SystemPool.by_name('newtest')
            self.assertEquals(pool.name, 'newtest')
            self.assertEquals(pool.description, 'newtestdesciprtion')
            self.assertEquals(pool.owner.user_name, self.owner.user_name)
            self.assertEquals(pool.access_policy.rules[0].everybody, True)

    def test_get_system_pool(self):
        response = requests.get(get_server_base() +
                'pools/%s/' % self.pool.name, headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['id'], self.pool.id)
        self.assertEquals(json['name'], self.pool.name)
        self.assertEquals(json['description'], self.pool.description)

    def test_update_system_pool(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                                                  'password': 'theowner'}).raise_for_status()
        response = patch_json(get_server_base() +
                'pools/%s/' % self.pool.name, session=s,
                data={'name': 'newname',
                      'description': 'newdescription',
                      'owner': {'user_name': self.user.user_name}})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.pool.name, 'newname')
            self.assertEquals(self.pool.description, 'newdescription')
            self.assertEquals(self.pool.owner.user_name, self.user.user_name)

        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.user.user_name,
                                                  'password': 'password'}).raise_for_status()
        response = patch_json(get_server_base() +
                              'pools/%s/' % self.pool.name, session=s,
                              data={'name': 'newname',
                                    'description': 'newdescription',
                                    'owner': {'group_name': self.group.group_name}})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.pool.owner, self.group)
            self.assertFalse(self.pool.owning_user)

    def test_add_system_to_pool(self):
        with session.begin():
            other_system = data_setup.create_system(owner=self.owner)
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                'password': 'theowner'}).raise_for_status()
        response = post_json(get_server_base() + 'pools/%s/systems/' % self.pool.name,
                session=s, data={'fqdn': other_system.fqdn})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertItemsEqual(self.pool.systems, [self.system, other_system])
            self.assertEquals(self.pool.activity[-1].field_name, 'System')
            self.assertEquals(self.pool.activity[-1].action, 'Added')
            self.assertEquals(self.pool.activity[-1].new_value, unicode(other_system))
            self.assertEquals(other_system.activity[-1].field_name, 'Pool')
            self.assertEquals(other_system.activity[-1].action, 'Added')
            self.assertEquals(other_system.activity[-1].new_value, unicode(self.pool))

        # adding to a pool that doesn't exist is a 404
        response = post_json(get_server_base() + 'pools/nosuchpool/systems/',
                session=s, data={'fqdn': other_system.fqdn})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.text, 'System pool nosuchpool does not exist')

        # adding a system that doesn't exist is a 400
        response = post_json(get_server_base() + 'pools/%s/systems/' % self.pool.name,
                session=s, data={'fqdn': 'nosuchsystem'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text, "System 'nosuchsystem' does not exist")


    def test_remove_system_from_pool(self):
        with session.begin():
            system = data_setup.create_system(owner=self.owner)
            pool = data_setup.create_system_pool(systems=[system])
        self.assertIn(system, pool.systems)
        s = requests.Session()

        # A system owner or a pool owner can remove a system from a pool
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                                                  'password': 'theowner'}).raise_for_status()
        response = s.delete(get_server_base() + 'pools/%s/systems?fqdn=%s' % (pool.name, system.fqdn))
        response.raise_for_status()

        with session.begin():
            session.expire_all()
            self.assertNotIn(system, pool.systems)
            self.assertEquals(pool.activity[-1].field_name, 'System')
            self.assertEquals(pool.activity[-1].action, 'Removed')
            self.assertEquals(pool.activity[-1].old_value, unicode(system))
            self.assertEquals(system.activity[-1].field_name, 'Pool')
            self.assertEquals(system.activity[-1].action, 'Removed')
            self.assertEquals(system.activity[-1].old_value, unicode(pool))


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

        unicode_pool = unicode(pool)
        self.assertIn(pool, system.pools)
        self.assertTrue(system.active_access_policy.grants
                        (self.user, SystemPermission.edit_system))
        # first as a random user
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': random_user.user_name,
                                                  'password': 'password'}).raise_for_status()
        response = s.delete(get_server_base() + 'pools/%s/' % pool_name)
        self.assertEquals(response.status_code, 403)

        # now as the pool owner
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': pool_owner.user_name,
                                                  'password': 'password'}).raise_for_status()
        response = s.delete(get_server_base() + 'pools/%s/' % pool_name)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            with self.assertRaises(NoResultFound):
                SystemPool.by_name(pool_name)

            self.assertNotIn(pool, system.pools)
            self.assertFalse(system.active_access_policy.grants
                             (self.user, SystemPermission.edit_system))

            self.assertEquals(system.activity[-1].field_name, 'Pool')
            self.assertEquals(system.activity[-1].action, 'Removed')
            self.assertEquals(system.activity[-1].old_value, unicode_pool)

            self.assertEquals(system.activity[-2].field_name, 'Active Access Policy')
            self.assertEquals(system.activity[-2].old_value, 'Pool policy: %s' % pool_name)
            self.assertEquals(system.activity[-2].new_value, 'Custom access policy')

            self.assertEquals(1, Activity.query
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

    def test_save_access_policy(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                                                  'password': 'theowner'}).raise_for_status()
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
            self.assertEquals(len(self.pool.access_policy.rules), 2)
            self.assertEquals(self.pool.access_policy.rules[0].permission,
                    SystemPermission.view)
            self.assertEquals(self.pool.access_policy.rules[1].permission,
                    SystemPermission.control_system)
            self.assertEquals(self.pool.access_policy.rules[1].everybody, True)

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

