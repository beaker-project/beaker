
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import email
import re

from turbogears.database import session

from bkr.inttest import data_setup, mail_capture_thread
from bkr.inttest.client import run_client, ClientError, create_client_config, ClientTestCase
from bkr.server.model import Group, Activity, GroupMembershipType


class GroupModifyTest(ClientTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'asdf')
            self.group = data_setup.create_group(owner=self.user)
            self.client_config = create_client_config(username=self.user.user_name,
                                                      password=u'asdf')

            rand_user = data_setup.create_user(password=u'asdf')
            self.group.add_member(rand_user)
            self.rand_client_config = create_client_config(username=rand_user.user_name,
                                                           password=u'asdf')

            admin = data_setup.create_admin(password=u'password')
            self.admin_client_config = create_client_config(username=admin.user_name,
                                                            password=u'password')

            self.fake_ldap_group = data_setup.create_group(
                    membership_type=GroupMembershipType.ldap)

    def check_notification(self, user, group, action):
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        self.assertEqual(rcpts, [user.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['To'], user.email_address)

        # headers and subject
        self.assertEqual(msg['X-Beaker-Notification'], 'group-membership')
        self.assertEqual(msg['X-Beaker-Group'], group.group_name)
        self.assertEqual(msg['X-Beaker-Group-Action'], action)
        for keyword in ['Group Membership', action, group.group_name]:
            self.assert_(keyword in msg['Subject'], msg['Subject'])

        # body
        msg_payload = msg.get_payload(decode=True)
        action = action.lower()
        for keyword in [action, group.group_name]:
            self.assert_(keyword in msg_payload, (keyword, msg_payload))

    def test_group_modify_no_criteria(self):
        try:
            out = run_client(['bkr', 'group-modify',
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Please specify an attribute to modify'
                         in e.stderr_output, e.stderr_output)


    def test_group_nonexistent(self):
        display_name = 'A New Group Display Name'
        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', display_name,
                              'group-like-non-other'],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Group group-like-non-other does not exist' in e.stderr_output,
                         e.stderr_output)

    def test_group_modify_invalid(self):
        display_name = 'A New Group Display Name'
        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', display_name,
                              'random', self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Exactly one group name must be specified' in
                         e.stderr_output, e.stderr_output)

    def test_group_modify_not_owner(self):
        display_name = 'A New Group Display Name'

        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', display_name,
                              self.group.group_name],
                             config = self.rand_client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('Cannot edit group', e.stderr_output)

    def test_group_modify_display_name(self):
        display_name = 'A New Group Display Name'
        out = run_client(['bkr', 'group-modify',
                          '--display-name', display_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertEquals(group.display_name, display_name)
            self.assertEquals(group.activity[-1].action, u'Changed')
            self.assertEquals(group.activity[-1].field_name, u'Display Name')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].new_value, display_name)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        try:
            out = run_client(['bkr', 'group-modify',
                              '--display-name', 'A really long display name'*20,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn(
                    'Group display name must be not more than 255 characters long',
                    e.stderr_output)

    def test_group_modify_group_name(self):
        group_name = u'mynewgroup'
        out = run_client(['bkr', 'group-modify',
                          '--group-name', group_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(group_name)
            self.assertEquals(group.group_name, group_name)
            self.assertEquals(group.activity[-1].action, u'Changed')
            self.assertEquals(group.activity[-1].field_name, u'Name')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].new_value, group_name)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        try:
            out = run_client(['bkr', 'group-modify',
                              '--group-name', 'areallylonggroupname'*20,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn(
                    'Group name must be not more than 255 characters long',
                    e.stderr_output)

    def test_group_modify_password(self):
        # Test successful hashed password change
        hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'
        run_client(['bkr', 'group-modify', '--root-password', hashed_password,
            self.group.group_name], config=self.client_config)
        session.expire(self.group)
        with session.begin():
            group = self.group
            self.assertEquals(group.root_password, hashed_password)
            self.assertEquals(group.activity[-1].action, u'Changed')
            self.assertEquals(group.activity[-1].field_name, u'Root Password')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        # Test successful cleartext password change
        good_password = data_setup.unique_name('Borrow or %srob?')
        run_client(['bkr', 'group-modify', '--root-password', good_password,
            self.group.group_name], config=self.client_config)
        session.expire(self.group)
        with session.begin():
            group = self.group
            self.assertEquals(group.root_password, good_password)
            self.assertEquals(group.activity[-1].action, u'Changed')
            self.assertEquals(group.activity[-1].field_name, u'Root Password')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        # Test unsuccessful cleartext password change
        short_password = 'fa1l'
        try:
            run_client(['bkr', 'group-modify', '--root-password', short_password,
                self.group.group_name], config=self.client_config)
            self.fail('Should fail with short password')
        except ClientError as e:
            # Number of req chars was changed in RPM, however RHEL is using older one
            # RHEL requires 7, Fedora requires 8 at this moment
            self.assertTrue(
                re.search('The group root password is shorter than . characters', str(e)))
            session.expire(self.group)
            with session.begin():
                group = self.group
                self.assertEquals(group.root_password, good_password)

    def test_group_modify_group_and_display_names(self):
        display_name = u'Shiny New Display Name'
        group_name = u'shinynewgroup'
        out = run_client(['bkr', 'group-modify',
                          '--display-name', display_name,
                          '--group-name', group_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(group_name)
            self.assertEquals(group.display_name, display_name)
            self.assertEquals(group.group_name, group_name)

    #https://bugzilla.redhat.com/show_bug.cgi?id=967799
    def test_group_modify_group_name_duplicate(self):
        with session.begin():
            group1 = data_setup.create_group(owner=self.user)
            group2 = data_setup.create_group(owner=self.user)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--group-name', group1.group_name,
                              group2.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Group %s already exists' % group1.group_name in e.stderr_output)

    def test_admin_cannot_rename_protected_group(self):
        # See https://bugzilla.redhat.com/show_bug.cgi?id=961206
        protected_group_name = u'admin'
        with session.begin():
            group = Group.by_name(protected_group_name)
            expected_display_name = group.display_name

        # Run command as the default admin user
        try:
            out = run_client(['bkr', 'group-modify',
                              '--group-name', 'new_admin',
                              '--display-name', 'this is also unchanged',
                              protected_group_name])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot rename protected group' in
                         e.stderr_output, e.stderr_output)

        # Check the whole request is ignored if the name change is rejected
        with session.begin():
            session.refresh(group)
            self.assertEquals(group.group_name, protected_group_name)
            self.assertEquals(group.display_name, expected_display_name)

        # However, changing just the display name is fine
        new_display_name = 'Tested admin group'
        out = run_client(['bkr', 'group-modify',
                          '--display-name', new_display_name,
                          protected_group_name])

        with session.begin():
            session.refresh(group)
            self.assertEquals(group.group_name, protected_group_name)
            self.assertEquals(group.display_name, new_display_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=960359
    def test_group_modify_description(self):
        description = 'This is a boring description'
        out = run_client(['bkr', 'group-modify',
                          '--description', description,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            self.assertEquals(self.group.description, description)

    def test_group_modify_add_member(self):
        with session.begin():
            user = data_setup.create_user()

        mail_capture_thread.start_capturing()

        out = run_client(['bkr', 'group-modify',
                          '--add-member', user.user_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assert_(user.user_name in
                         [u.user_name for u in group.users])

        self.check_notification(user, group, action='Added')

        try:
            out = run_client(['bkr', 'group-modify',
                              '--add-member', 'idontexist',
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('User idontexist does not exist' in
                         e.stderr_output, e.stderr_output)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--add-member', user.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('User %s is already a member of group %s'
                % (user.user_name, self.group.group_name)
                in e.stderr_output, e.stderr_output)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'User')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].new_value, user.user_name)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        try:
            out = run_client(['bkr', 'group-modify',
                              '--add-member', user.user_name,
                              self.fake_ldap_group.group_name])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot edit membership of group %s'
                         % self.fake_ldap_group.group_name
                         in e.stderr_output,e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1328313
    def test_group_modify_add_multiple_members(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()

        out = run_client(['bkr', 'group-modify',
                          '--add-member', user1.user_name,
                          '--add-member', user2.user_name,
                          self.group.group_name],
                         config=self.client_config)
        with session.begin():
            session.refresh(self.group)
            self.assertIn(user1, self.group.users)
            self.assertIn(user2, self.group.users)

    def test_group_modify_remove_member(self):
        with session.begin():
            user = data_setup.create_user()
            self.group.add_member(user)
            session.flush()
            self.assert_(user in self.group.users)

        mail_capture_thread.start_capturing()

        out = run_client(['bkr', 'group-modify',
                          '--remove-member', user.user_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assert_(user.user_name not in
                         [u.user_name for u in group.users])

        self.check_notification(user, group, action='Removed')
        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertEquals(group.activity[-1].action, u'Removed')
            self.assertEquals(group.activity[-1].field_name, u'User')
            self.assertEquals(group.activity[-1].user.user_id,
                              self.user.user_id)
            self.assertEquals(group.activity[-1].old_value, user.user_name)
            self.assertEquals(group.activity[-1].new_value, None)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', 'idontexist',
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('User idontexist does not exist' in
                         e.stderr_output, e.stderr_output)
        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', user.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('User %s is not a member of group %s'
                         % (user.user_name, self.group.group_name)
                        in e.stderr_output, e.stderr_output)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', self.user.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot remove user' in
                         e.stderr_output, e.stderr_output)

        # remove the last group member/owner as 'admin'
        mail_capture_thread.start_capturing()
        out = run_client(['bkr', 'group-modify',
                          '--remove-member', self.user.user_name,
                          self.group.group_name], config=self.admin_client_config)
        self.check_notification(self.user, self.group, action='Removed')

        # try to remove self from admin group
        # first remove all other users except 'admin'
        group = Group.by_name(u'admin')
        group_users = group.users
        # remove  all other users from 'admin'
        for usr in group_users:
            if usr.user_id != 1:
                out = run_client(['bkr', 'group-modify',
                                  '--remove-member', usr.user_name,
                                  'admin'], config=self.admin_client_config)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', 'admin', 'admin'])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot remove user' in
                         e.stderr_output, e.stderr_output)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', user.user_name,
                              self.fake_ldap_group.group_name])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot edit membership of group %s'
                          % self.fake_ldap_group.group_name
                          in e.stderr_output, e.stderr_output)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1336966
    def test_group_modify_remove_multiple_members(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            self.group.add_member(user1)
            self.group.add_member(user2)
            session.flush()
            self.assert_(user1 in self.group.users)
            self.assert_(user2 in self.group.users)

        out = run_client(['bkr', 'group-modify',
                          '--remove-member', user1.user_name,
                          '--remove-member', user2.user_name,
                          self.group.group_name],
                         config=self.client_config)

        with session.begin():
            session.refresh(self.group)
            self.assertNotIn(user1, self.group.users)
            self.assertNotIn(user2, self.group.users)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1336966
    def test_subsequent_user_after_fail_not_removed(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            self.group.add_member(user2)
            session.flush()
            self.assertNotIn(user1, self.group.users)
            self.assertIn(user2, self.group.users)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--remove-member', user1.user_name,
                              '--remove-member', user2.user_name,
                              self.group.group_name],
                             config=self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('User %s is not a member of group %s'
                         % (user1.user_name, self.group.group_name)
                         in e.stderr_output, e.stderr_output)
            self.assertIn(user2, self.group.users)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1336966
    def test_subsequent_user_after_fail_not_added(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            self.group.add_member(user1)
            session.flush()
            self.assertIn(user1, self.group.users)
            self.assertNotIn(user2, self.group.users)

        try:
            out = run_client(['bkr', 'group-modify',
                              '--add-member', user1.user_name,
                              '--add-member', user2.user_name,
                              self.group.group_name],
                             config=self.client_config)
            self.fail('should raise')
        except ClientError as e:
            self.assert_('User %s is already a member of group %s'
                         % (user1.user_name, self.group.group_name)
                         in e.stderr_output, e.stderr_output)
            self.assertNotIn(user2, self.group.users)

    def test_group_modify_grant_owner(self):
        with session.begin():
            user1 = data_setup.create_user()
            self.group.add_member(user1)
            user2 = data_setup.create_user()
            self.group.add_member(user2)
            user3 = data_setup.create_user()

        out = run_client(['bkr', 'group-modify',
                          '--grant-owner', user1.user_name,
                          '--grant-owner', user2.user_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assert_(user1.user_id in [u.user_id for u in group.owners()])
            self.assert_(user2.user_id in [u.user_id for u in group.owners()])
            self.assertEquals(Activity.query.filter_by(service=u'HTTP',
                                                       field_name=u'Owner', action=u'Added',
                                                       new_value=user2.user_name).count(), 1)
            group = Group.by_name(group.group_name)
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].new_value, user2.user_name)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        # If the user is not a group member, add the user into the members list
        # first and then grant the group ownership.
        out = run_client(['bkr', 'group-modify',
                          '--grant-owner', user3.user_name,
                          self.group.group_name],
                         config = self.client_config)
        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assertIn(user3, group.users)
            self.assertTrue(group.has_owner(user3))

        try:
            out = run_client(['bkr', 'group-modify',
                              '--grant-owner', user3.user_name,
                              self.fake_ldap_group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot edit ownership of group' in e.stderr_output, e.stderr_output)

    def test_inverted_group_modify_grant_owner(self):
        with session.begin():
            group = data_setup.create_group(owner=self.user,
                    membership_type=GroupMembershipType.inverted)
            user1 = data_setup.create_user()
            group.add_member(user1)
            user2 = data_setup.create_user()
            group.add_member(user2)
            # user3 is not associated but can also be set as the group owner.
            user3 = data_setup.create_user()

        out = run_client(['bkr', 'group-modify',
                          '--grant-owner', user1.user_name,
                          '--grant-owner', user2.user_name,
                          '--grant-owner', user3.user_name,
                          group.group_name],
                         config = self.client_config)

        with session.begin():
            session.expire_all()
            self.assertTrue(group.has_owner(user1))
            self.assertTrue(group.has_owner(user2))
            self.assertTrue(group.has_owner(user3))
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].new_value, user3.user_name)
            self.assertEquals(group.activity[-1].service, u'HTTP')

    def test_group_modify_revoke_owner(self):
        with session.begin():
            user1 = data_setup.create_user()
            self.group.add_member(user1)
            user2 = data_setup.create_user()
            self.group.add_member(user2)
            user3 = data_setup.create_user()

        out = run_client(['bkr', 'group-modify',
                          '--grant-owner', user1.user_name,
                          '--grant-owner', user2.user_name,
                          self.group.group_name],
                         config = self.client_config)

        out = run_client(['bkr', 'group-modify',
                          '--revoke-owner', user1.user_name,
                          '--revoke-owner', user2.user_name,
                          self.group.group_name],
                         config = self.client_config)

        with session.begin():
            session.refresh(self.group)
            group = Group.by_name(self.group.group_name)
            self.assert_(user1.user_id not in [u.user_id for u in group.owners()])
            self.assert_(user2.user_id not in [u.user_id for u in group.owners()])
            self.assertEquals(Activity.query.filter_by(service=u'HTTP',
                                                       field_name=u'Owner', action=u'Removed',
                                                       old_value=user2.user_name).count(), 1)
            self.assertEquals(group.activity[-1].action, u'Removed')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].old_value, user2.user_name)
            self.assertEquals(group.activity[-1].service, u'HTTP')

        try:
            out = run_client(['bkr', 'group-modify',
                              '--revoke-owner', user3.user_name,
                              self.group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('User is not a member of group' in e.stderr_output)
        try:
            out = run_client(['bkr', 'group-modify',
                              '--revoke-owner', user3.user_name,
                              self.fake_ldap_group.group_name],
                             config = self.client_config)
            self.fail('Must fail or die')
        except ClientError as e:
            self.assert_('Cannot edit ownership of group' in e.stderr_output, e.stderr_output)

    def test_escapes_uri_characters_in_group_name(self):
        bad_group_name = u'!@#$%^&*()_+{}|:><?'
        with session.begin():
            group = data_setup.create_group(group_name=bad_group_name)
        run_client(['bkr', 'group-modify', bad_group_name, '--display-name', 'a'])
        run_client(['bkr', 'group-modify', bad_group_name, '--add-member', self.user.user_name])
        run_client(['bkr', 'group-modify', bad_group_name, '--grant-owner', self.user.user_name])
        run_client(['bkr', 'group-modify', bad_group_name, '--revoke-owner', self.user.user_name])
        run_client(['bkr', 'group-modify', bad_group_name, '--remove-member', self.user.user_name])
