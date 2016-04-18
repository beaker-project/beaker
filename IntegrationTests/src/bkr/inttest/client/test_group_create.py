
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.server.model import Group, GroupMembershipType, User
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, create_client_config, \
        ClientTestCase

class GroupCreateTest(ClientTestCase):

    def test_group_create(self):
        group_name = data_setup.unique_name(u'group%s')
        display_name = u'My Group'
        out = run_client(['bkr', 'group-create',
                          '--display-name', display_name,
                          group_name])
        self.assert_('Group created' in out, out)
        with session.begin():
            group = Group.by_name(group_name)
            self.assertEquals(group.display_name, display_name)
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].new_value, data_setup.ADMIN_USER)
            self.assertEquals(group.activity[-1].service, u'XMLRPC')
            self.assertEquals(group.activity[-2].action, u'Added')
            self.assertEquals(group.activity[-2].field_name, u'User')
            self.assertEquals(group.activity[-2].new_value, data_setup.ADMIN_USER)
            self.assertEquals(group.activity[-2].service, u'XMLRPC')
            self.assertEquals(group.activity[-3].action, u'Created')
            self.assertEquals(group.activity[-3].service, u'XMLRPC')

        group_name = data_setup.unique_name(u'group%s')
        out = run_client(['bkr', 'group-create',
                          group_name])
        self.assert_('Group created' in out, out)

        with session.begin():
            group = Group.by_name(group_name)
            self.assertEqual(group.group_name, group_name)
            self.assertEqual(group.display_name, group_name)

        group_name = data_setup.unique_name(u'group%s')

        try:
            out = run_client(['bkr', 'group-create',
                          group_name, group_name])
            self.fail('Must fail or die')
        except ClientError,e:
            self.assert_('Exactly one group name must be specified' in
                         e.stderr_output, e.stderr_output)
        try:
            out = run_client(['bkr', 'group-create',
                              'areallylonggroupname'*20])
            self.fail('Must fail or die')
        except ClientError,e:
            self.assertIn(
                    'Group display name must be not more than 255 characters long',
                    e.stderr_output)
        try:
            out = run_client(['bkr', 'group-create',
                              '--display-name',
                              'A really long group display name'*20,
                              'agroup'])
            self.fail('Must fail or die')
        except ClientError,e:
            self.assertIn(
                    'Group display name must be not more than 255 characters long',
                    e.stderr_output)

    def test_ldap_group(self):

        group_name = u'wyfp'
        display_name = u'My LDAP Group'
        out = run_client(['bkr', 'group-create', '--ldap',
                          '--display-name', display_name,
                          group_name])

        group = Group.by_name(group_name)
        self.assertEquals(group.membership_type, GroupMembershipType.ldap)
        self.assertEquals(group.users, [User.by_user_name(u'asaha')])

        with session.begin():
            rand_user = data_setup.create_user(password = 'asdf')

        rand_client_config = create_client_config(username=rand_user.user_name,
                                                  password='asdf')

        group_name = u'alp'
        display_name = u'ALP'
        try:
            out = run_client(['bkr', 'group-create', '--ldap',
                          '--display-name', display_name,
                              group_name],
                             config = rand_client_config)
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('Only admins can create LDAP groups' in
                         e.stderr_output)

    def test_group_passwords(self):
        group_name = data_setup.unique_name(u'group%s')

        try:
            out = run_client(['bkr', 'group-create',
                              '--root-password', 'fail',
                              group_name])
            self.fail('Expected to fail due to short password')
        except ClientError, e:
            self.assertTrue('Root password is too short' in e.stderr_output,
                e.stderr_output)

        try:
            out = run_client(['bkr', 'group-create',
                              '--root-password', 'melanoma',
                              group_name])

            self.fail('Expected to fail due to dictionary words')
        except ClientError, e:
            self.assertTrue('Root password is based on a dictionary word' in
                e.stderr_output, e.stderr_output)
        out = run_client(['bkr', 'group-create',
                          '--root-password', 'Borrow or rob?',
                          group_name])
        self.assertTrue('Group created' in out)

    def test_group_duplicate(self):
        group_name = data_setup.unique_name(u'group%s')
        display_name = u'My Group'
        out = run_client(['bkr', 'group-create',
                          '--display-name', display_name,
                          group_name])

        self.assert_('Group created' in out, out)

        try:
            out = run_client(['bkr', 'group-create',
                              group_name])
            self.fail('Must fail or die')
        except ClientError,e:
            self.assert_('Group already exists' in e.stderr_output,
                         e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=960359
    def test_group_description(self):
        group_name = data_setup.unique_name(u'group%s')
        description = 'This is a boring group'
        out = run_client(['bkr', 'group-create',
                          '--description', description,
                          group_name])
        self.assert_('Group created' in out, out)
        with session.begin():
            group = Group.by_name(group_name)
            self.assertEquals(group.description, description)
