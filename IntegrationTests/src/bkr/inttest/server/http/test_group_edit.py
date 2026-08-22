# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from six import assertCountEqual, text_type
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as requests_login, \
        patch_json, post_json
from bkr.server.database import session
from bkr.server.model import Activity, Group, GroupMembershipType, \
        SystemPermission, User


class GroupHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by the group editing page.
    """
    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
            self.group = data_setup.create_group(owner=self.user)
            self.inverted_group = data_setup.create_group(
                    owner=self.user,
                    membership_type=GroupMembershipType.inverted)

    def test_get_group(self):
        response = requests.get(get_server_base() +
                'groups/%s' % self.group.group_name, headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['id'], self.group.id)
        self.assertEqual(json['group_name'], self.group.group_name)
        self.assertEqual(json['display_name'], self.group.display_name)

    def test_create_new_group(self):
        s = requests.Session()
        requests_login(s, user=self.user, password=u'password')
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': 'FBZ',
            'display_name': 'Group FBZ',
            'description': 'Group FBZ description',
            'root_password': 'blapppy7',
        })
        response.raise_for_status()
        with session.begin():
            group = Group.by_name(u'FBZ')
            self.assertEqual(group.display_name, u'Group FBZ')
            self.assertEqual(group.description, u'Group FBZ description')
            self.assertTrue(group.has_owner(self.user))
            self.assertEqual(group.activity[-1].action, u'Added')
            self.assertEqual(group.activity[-1].field_name, u'Owner')
            self.assertEqual(group.activity[-1].new_value, self.user.user_name)
            self.assertEqual(group.activity[-1].service, u'HTTP')
            self.assertEqual(group.activity[-2].action, u'Added')
            self.assertEqual(group.activity[-2].field_name, u'User')
            self.assertEqual(group.activity[-2].new_value, self.user.user_name)
            self.assertEqual(group.activity[-2].service, u'HTTP')
            self.assertEqual(group.activity[-3].action, u'Created')
            self.assertEqual(group.activity[-3].service, u'HTTP')
            self.assertEqual('blapppy7', group.root_password)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1469345
    def test_create_group_invalid_group_name_throws_error(self):
        s = requests.Session()
        requests_login(s, user=self.user, password=u'password')

        # group name exceeds valid length
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': 'grouplongname'*20,
            'display_name': 'groupdisplayname',
            'description': 'grouplongname description',
            'root_password': 'blapppy7',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Group name must be not more than 255 characters long',
                      response.text)

        # group name contains leading spaces
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': '  containsspace',
            'display_name': 'groupdisplayname',
            'description': 'grouplongname description',
            'root_password': 'blapppy7',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Group name must not contain leading or trailing whitespace',
                      response.text)

        # group name contains forward slash
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': 'group/name',
            'display_name': 'groupdisplayname',
            'description': 'grouplongname description',
            'root_password': 'blapppy7',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Group name cannot contain \'/\'', response.text)


    def test_create_ldap_group_with_old_format(self):
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': 'my_ldap_group',
            'display_name': 'My LDAP group',
            'ldap': True,
        })
        response.raise_for_status()
        with session.begin():
            group = Group.by_name(u'my_ldap_group')
            self.assertEqual(group.membership_type, GroupMembershipType.ldap)
            self.assertEqual(group.users, [User.by_user_name(u'my_ldap_user')])
            # The LDAP group should have no owner.
            self.assertEqual(len(group.owners()), 0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_create_ldap_group_with_new_format(self):
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': u'another_my_ldap_group',
            'display_name': u'Another My LDAP group',
            'membership_type': u'ldap',
        })
        response.raise_for_status()
        with session.begin():
            group = Group.by_name(u'another_my_ldap_group')
            self.assertEqual(group.membership_type, GroupMembershipType.ldap)
            self.assertEqual(group.users,
                    [User.by_user_name(u'another_my_ldap_user')])
            # The LDAP group should have no owner.
            self.assertEqual(len(group.owners()), 0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_create_inverted_group(self):
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'groups/', session=s, data={
            'group_name': 'my_inverse_group',
            'display_name': 'My INVERSE group',
            'membership_type': u'inverted',
        })
        response.raise_for_status()
        with session.begin():
            group = Group.by_name(u'my_inverse_group')
            self.assertEqual(group.membership_type,
                              GroupMembershipType.inverted)

    def test_update_group(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'group_name': u'newname',
                      'display_name': u'newdisplayname',
                      'root_password': u'$1$NaCl$O34mAzBXtER6obhoIodu8.'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.group.group_name, u'newname')
            self.assertEqual(self.group.display_name, u'newdisplayname')
            self.assertEqual(self.group.root_password, u'$1$NaCl$O34mAzBXtER6obhoIodu8.')

    # https://bugzilla.redhat.com/show_bug.cgi?id=960359
    def test_update_group_description(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'description': u'newdescription'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.group.description, u'newdescription')
            self.assertEqual(self.group.activity[-1].action, u'Changed')
            self.assertEqual(self.group.activity[-1].field_name, u'Description')
            self.assertEqual(self.group.activity[-1].new_value, u'newdescription')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_update_a_group_to_LDAP_group_with_old_format(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'ldap': True})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.group.membership_type, GroupMembershipType.ldap)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_update_a_group_to_LDAP_group_with_new_format(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'membership_type': u'ldap'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.group.membership_type, GroupMembershipType.ldap)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_can_update_a_group_to_inverted_group(self):
        s = requests.Session()
        requests_login(s)
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'membership_type': u'inverted'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.group.membership_type,
                              GroupMembershipType.inverted)

    def test_cannot_update_group_with_empty_name_or_display_name(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'group_name': ''})
        self.assertEqual(400, response.status_code)
        self.assertEqual('Group name cannot be empty', response.text)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'display_name': ''})
        self.assertEqual(400, response.status_code)
        self.assertEqual('Group display name cannot be empty', response.text)

    def test_cannot_update_group_with_leading_space_or_trailing_space(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'group_name': u' new name '})
        self.assertEqual(400, response.status_code)
        self.assertEqual('Group name must not contain leading or trailing whitespace',
                          response.text)

        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'display_name': u' new display name '})
        self.assertEqual(400, response.status_code)
        self.assertEqual('Group display name must not contain leading or trailing whitespace',
                          response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1263921
    def test_cannot_update_group_name_with_forward_slash(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = patch_json(get_server_base() +
                'groups/%s' % self.group.group_name, session=s,
                data={'group_name': u'notanother/'})
        self.assertEqual(400, response.status_code)
        self.assertEqual('Group name cannot contain \'/\'', response.text)

    def test_unauthenticated_user_cannot_add_permission(self):
        with session.begin():
            permission = data_setup.create_permission()
        s = requests.Session()
        response = post_json(get_server_base() + 'groups/%s/permissions/' % self.group.group_name,
                session=s, data={'permission_name': permission.permission_name})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.text, 'Authenticated user required')

    def test_non_admin_cannot_add_permission(self):
        with session.begin():
            permission = data_setup.create_permission()
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/permissions/' % self.group.group_name,
                session=s, data={'permission_name': permission.permission_name})
        self.assertEqual(response.status_code, 403)
        self.assertIn('You are not a member of the admin group', response.text)

    def test_admin_can_add_permssion(self):
        with session.begin():
           permission = data_setup.create_permission()
        s = requests.Session()
        requests_login(s, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        response = post_json(get_server_base() + 'groups/%s/permissions/' % self.group.group_name,
               session=s, data={'permission_name': permission.permission_name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            assertCountEqual(self, self.group.permissions, [permission])
            self.assertEqual(self.group.activity[-1].field_name, 'Permission')
            self.assertEqual(self.group.activity[-1].action, 'Added')
            self.assertEqual(self.group.activity[-1].new_value,
                    text_type(permission)[:Activity.new_value.type.length])

    def test_adding_permission_to_nonexistent_group_raises_an_error(self):
        with session.begin():
           permission = data_setup.create_permission()
        s = requests.Session()
        requests_login(s, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        response = post_json(get_server_base() + 'groups/nosuchgroup/permissions/',
                session=s, data={'permission_name': permission.permission_name})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, 'Group nosuchgroup does not exist')

    def test_adding_nonexistent_permission_raises_an_error(self):
        s = requests.Session()
        requests_login(s, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        response = post_json(get_server_base() + 'groups/%s/permissions/' % self.group.group_name,
                session=s, data={'permission_name': 'nosuchpermission'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "Permission 'nosuchpermission' does not exist")

    def test_unauthenticated_user_cannot_remove_permission(self):
        with session.begin():
            permission = data_setup.create_permission()
            self.group.permissions.append(permission)
        s = requests.Session()
        response = s.delete(get_server_base() +
            'groups/%s/permissions?permission_name=%s' % (self.group.group_name,
                                                  permission.permission_name))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.text, 'Authenticated user required')

    def test_can_remove_permission(self):
        with session.begin():
            permission = data_setup.create_permission()
            self.group.permissions.append(permission)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = s.delete(get_server_base() +
            'groups/%s/permissions?permission_name=%s' % (self.group.group_name,
                                                  permission.permission_name))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertNotIn(permission, self.group.permissions)
            session.refresh(permission)
            self.assertEqual(self.group.activity[-1].field_name, 'Permission')
            self.assertEqual(self.group.activity[-1].action, 'Removed')
            self.assertEqual(self.group.activity[-1].old_value,
                    text_type(permission)[:Activity.old_value.type.length])

    def test_non_group_owner_cannot_modify_membership(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/members/' % self.group.group_name,
                session=s, data={'user': user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot edit membership', response.text)

    def test_cannot_add_member_to_ldap_group(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            ldap_group = data_setup.create_group(membership_type=GroupMembershipType.ldap)
        s = requests.Session()
        requests_login(s, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        response = post_json(get_server_base() + 'groups/%s/members/' % ldap_group.group_name,
                session=s, data={'user_name': user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cannot edit membership of group %s" %
                                ldap_group.group_name, response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_add_deleted_account_as_member(self):
        with session.begin():
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'groups/%s/members/' % self.group.group_name,
                session=s, data={'user_name': deleted_user.user_name})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot add deleted user %s to group' % deleted_user.user_name)

    def test_can_add_member(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/members/' % self.group.group_name,
                session=s, data={'user_name': user.user_name, 'is_owner': True})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIn(user, self.group.users)
            self.assertTrue(self.group.has_owner(user))
            self.assertEqual(self.group.activity[-1].user, self.user)
            self.assertEqual(self.group.activity[-1].field_name, 'Owner')
            self.assertEqual(self.group.activity[-1].action, 'Added')
            self.assertEqual(self.group.activity[-1].new_value, text_type(user))
            self.assertEqual(self.group.activity[-2].user, self.user)
            self.assertEqual(self.group.activity[-2].field_name, 'User')
            self.assertEqual(self.group.activity[-2].action, 'Added')
            self.assertEqual(self.group.activity[-2].new_value, text_type(user))

    def test_can_remove_member(self):
        with session.begin():
            user = data_setup.create_user()
            self.group.add_member(user)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = s.delete(get_server_base() +
            'groups/%s/members/?user_name=%s' % (self.group.group_name, user.user_name))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertNotIn(user, self.group.users)
            self.assertEqual(self.group.activity[-1].user, self.user)
            self.assertEqual(self.group.activity[-1].field_name, 'User')
            self.assertEqual(self.group.activity[-1].action, 'Removed')
            self.assertEqual(self.group.activity[-1].old_value, text_type(user))

    def test_cannot_modify_ownership_on_unowned_group(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/owners/' % self.group.group_name,
                session=s, data={'user_name': user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot edit ownership', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_cannot_modify_ownership_of_a_LDAP_group(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            ldap_group = data_setup.create_group(membership_type=GroupMembershipType.ldap)
        s = requests.Session()
        requests_login(s, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        response = post_json(get_server_base() + 'groups/%s/owners/' % ldap_group.group_name,
                session=s, data={'user_name': user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot edit ownership', response.text)

    def test_can_grant_ownership_to_group_member(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            self.group.add_member(user)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/owners/' % self.group.group_name,
                session=s, data={'user_name': user.user_name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.group.has_owner(user))
            self.assertEqual(self.group.activity[-1].user, self.user)
            self.assertEqual(self.group.activity[-1].field_name, 'Owner')
            self.assertEqual(self.group.activity[-1].action, 'Added')
            self.assertEqual(self.group.activity[-1].new_value, text_type(user))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1308625
    def test_can_grant_ownership_to_additional_users_on_inverted_groups(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            group = data_setup.create_group(owner=user,
                membership_type=GroupMembershipType.inverted)
            user2 = data_setup.create_user()
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        # add user2 to the group owners list
        response = post_json(get_server_base() + 'groups/%s/owners/' % group.group_name,
                session=s, data={'user_name': user2.user_name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(group.has_owner(user2))

    def test_can_grant_ownership_to_non_group_member(self):
        with session.begin():
            user = data_setup.create_user()
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/owners/' % self.group.group_name,
                session=s, data={'user_name': user.user_name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIn(user, self.group.users)
            self.assertTrue(self.group.has_owner(user))
            self.assertEqual(self.group.activity[-1].user, self.user)
            self.assertEqual(self.group.activity[-1].field_name, 'Owner')
            self.assertEqual(self.group.activity[-1].action, 'Added')
            self.assertEqual(self.group.activity[-1].new_value, text_type(user))
            self.assertEqual(self.group.activity[-2].user, self.user)
            self.assertEqual(self.group.activity[-2].field_name, 'User')
            self.assertEqual(self.group.activity[-2].action, 'Added')
            self.assertEqual(self.group.activity[-2].new_value, text_type(user))

    def test_can_revoke_ownership(self):
        with session.begin():
            user = data_setup.create_user()
            self.group.add_member(user, is_owner=True)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = s.delete(get_server_base() +
            'groups/%s/owners/?user_name=%s' % (self.group.group_name, user.user_name))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertFalse(self.group.has_owner(user))
            self.assertIn(user, self.group.users)
            self.assertEqual(self.group.activity[-1].user, self.user)
            self.assertEqual(self.group.activity[-1].field_name, 'Owner')
            self.assertEqual(self.group.activity[-1].action, 'Removed')
            self.assertEqual(self.group.activity[-1].old_value, text_type(user))

    def test_cannot_remove_the_only_owner(self):
        """
        User without admin permission cannot remove the only owner of a group.
        """
        with session.begin():
            user = data_setup.create_user(password=u'password')
            group = data_setup.create_group(owner=user)
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = s.delete(get_server_base() +
            'groups/%s/owners/?user_name=%s' % (group.group_name, user.user_name))
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot remove the only owner', response.text)

    def test_can_remove_the_only_owner_by_admin(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            group = data_setup.create_group(owner=user)
        s = requests.Session()
        requests_login(s, user=data_setup.ADMIN_USER, password=data_setup.ADMIN_PASSWORD)
        response = s.delete(get_server_base() +
            'groups/%s/owners/?user_name=%s' % (group.group_name, user.user_name))
        with session.begin():
            session.refresh(group)
            self.assertFalse(group.has_owner(user))
            self.assertEqual(group.owners(), [])

    def test_delete_group(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = s.delete(get_server_base() + 'groups/%s' % self.group.group_name)
        response.raise_for_status()
        with session.begin():
            self.assertEqual(0,
                Group.query.filter_by(group_id=self.group.group_id).count())
            self.assertEqual(1, Activity.query
                .filter(Activity.field_name == u'Group')
                .filter(Activity.action == u'Removed')
                .filter(Activity.old_value == self.group.display_name).count(),
                'Expected to find activity record for group removal')

    def test_regular_member_cannot_delete_group(self):
        with session.begin():
            member = data_setup.create_user(password=u'unprivileged')
            self.group.add_member(member)
        s = requests.Session()
        requests_login(s, user=member.user_name, password=u'unprivileged')
        response = s.delete(get_server_base() + 'groups/%s' % self.group.group_name)
        self.assertEqual(response.status_code, 403)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1102617
    def test_cannot_delete_protected_group(self):
        # 'admin' group is created by beaker-init, it always exists
        s = requests.Session()
        requests_login(s)
        response = s.delete(get_server_base() + 'groups/admin')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "Group 'admin' is predefined and cannot be deleted")

    # https://bugzilla.redhat.com/show_bug.cgi?id=968843
    def test_cannot_delete_group_which_has_submitted_jobs(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user, group=self.group)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = s.delete(get_server_base() + 'groups/%s' % self.group.group_name)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot delete a group which has associated jobs')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1085703
    # https://bugzilla.redhat.com/show_bug.cgi?id=1132730
    def test_deleting_group_with_access_policy_references(self):
        """
        When deleting a group which is granted permissions in a system access 
        policy, the access policy rules should be removed.
        """
        with session.begin():
            group = data_setup.create_group(group_name=u'LNP')
            system = data_setup.create_system(shared=False)
            system.custom_access_policy.add_rule(group=group,
                    permission=SystemPermission.edit_system)
            # There will be two rules, one is the default "everyone view".
            self.assertEqual(len(system.custom_access_policy.rules), 2)
        s = requests.Session()
        requests_login(s)
        response = s.delete(get_server_base() + 'groups/%s' % group.group_name)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(system.custom_access_policy.rules), 1)
            self.assertEqual(system.activity[0].field_name, u'Access Policy Rule')
            self.assertEqual(system.activity[0].action, u'Removed')
            self.assertEqual(system.activity[0].old_value,
                    u'Group:LNP:edit_system')

    #https://bugzilla.redhat.com/show_bug.cgi?id=1199368
    def test_deleting_group_with_pool(self):
        """
        When deleting a group which owns a system pool, the pool should 
        become owned by the user doing the deletion.
        """
        with session.begin():
            user = data_setup.create_user(password='testing')
            group = data_setup.create_group(owner=user)
            pool = data_setup.create_system_pool(owning_group=group)
        s = requests.Session()
        requests_login(s)
        response = s.delete(get_server_base() + 'groups/%s' % group.group_name)
        response.raise_for_status()
        with session.begin():
            session.refresh(pool)
            self.assertIsNone(pool.owning_group)
            self.assertEqual(pool.owning_user.user_name, data_setup.ADMIN_USER)
            self.assertEqual(pool.activity[-1].action, u'Changed')
            self.assertEqual(pool.activity[-1].field_name, u'Owner')
            self.assertEqual(pool.activity[-1].old_value, group.group_name)
            self.assertEqual(pool.activity[-1].new_value, data_setup.ADMIN_USER)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_cannnot_exclude_user_from_a_normal_group(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/excluded-users/' %
                self.group.group_name, session=s,
                data={'user_name': self.user.user_name})
        self.assertEqual(response.status_code, 404)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_cannnot_exclude_user_who_is_the_only_owner(self):
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/excluded-users/' %
                self.inverted_group.group_name, session=s,
                data={'user_name': self.user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertIn('Cannot exclude user %s' % self.user, response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_can_exclude_user(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            self.assertIn(user, self.inverted_group.users)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = post_json(get_server_base() + 'groups/%s/excluded-users/' %
                self.inverted_group.group_name, session=s,
                data={'user_name': user.user_name})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertNotIn(user, self.inverted_group.users)
            self.assertEqual(self.inverted_group.activity[-1].user, self.user)
            self.assertEqual(self.inverted_group.activity[-1].field_name, u'User')
            self.assertEqual(self.inverted_group.activity[-1].action, u'Excluded')
            self.assertEqual(self.inverted_group.activity[-1].new_value, text_type(user))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_can_readd_user(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            self.inverted_group.exclude_user(user)
        with session.begin():
            session.expire_all()
            self.assertNotIn(user, self.inverted_group.users)
        s = requests.Session()
        requests_login(s, user=self.user.user_name, password=u'password')
        response = s.delete(get_server_base() +
            'groups/%s/excluded-users/?user_name=%s' %
                    (self.inverted_group.group_name, user.user_name))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertIn(user, self.inverted_group.users)
            self.assertEqual(self.inverted_group.activity[-1].user, self.user)
            self.assertEqual(self.inverted_group.activity[-1].field_name, 'User')
            self.assertEqual(self.inverted_group.activity[-1].action, 'Re-added')
            self.assertEqual(self.inverted_group.activity[-1].old_value, text_type(user))

# There are no callers of the group XMLRPC methods left in Beaker itself, but 
# we still support the XMLRPC methods for older client versions and other 
# people's scripts, etc.
