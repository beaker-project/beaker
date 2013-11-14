import crypt
import requests
from turbogears.database import session
from bkr.server.model import Group, User, Activity, UserGroup
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction, mail_capture
from bkr.inttest.server.webdriver_utils import login, logout, is_text_present, \
        wait_for_animation, delete_and_confirm
from bkr.inttest.assertions import wait_for_condition
import email

class TestGroupsWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password='password')
            self.group = data_setup.create_group()
            self.perm1 = data_setup.create_permission()
            self.user.groups.append(self.group)
        self.browser = self.get_browser()
        self.clear_password = 'gyfrinachol'
        self.hashed_password = '$1$NaCl$O34mAzBXtER6obhoIodu8.'
        self.simple_password = 's3cr3t'

        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()
        self.browser.quit()

    def test_add_bad_permission(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_id('Permissions_permissions_text').send_keys('dummy_perm')
        b.find_element_by_id('Permissions').submit()
        #Test that it has not been dynamically added
        b.find_element_by_xpath('//span[@id="response_Permissions_failure" and '
                'text()="Invalid permission value"]')

        #Double check that it wasn't added to the permissions
        b.find_element_by_xpath('//table[@id="group_permission_grid" and '
                'not(.//td/text()="dummy_perm")]')

        #Triple check it was not persisted to the DB
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_xpath('//table[@id="group_permission_grid" and '
                'not(.//td/text()="dummy_perm")]')

    def test_add_and_remove_permission(self):
        b = self.browser
        login(b)

        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_id('Permissions_permissions_text').send_keys(self.perm1.permission_name)
        b.find_element_by_id('Permissions').submit()
        #Test that permission dynamically updated
        b.find_element_by_xpath('//table[@id="group_permission_grid"]//td[text()="%s"]'
                % self.perm1.permission_name)

        #Test that the permission was persisted by reopening the current page
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_xpath('//table[@id="group_permission_grid"]//td[text()="%s"]'
                % self.perm1.permission_name)

        #Let's try and remove it
        delete_and_confirm(b, '//td[preceding-sibling::td/text()="%s"]'
                % self.perm1.permission_name, 'Remove')
        #Check it has been removed from the table
        b.find_element_by_xpath('//table[@id="group_permission_grid" and '
                'not(.//td/text()="%s")]' % self.perm1.permission_name)

        #Reload to make sure it has been removed from the DB
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_xpath('//table[@id="group_permission_grid" and '
                'not(.//td/text()="%s")]' % self.perm1.permission_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1012373
    def test_add_then_immediately_remove_permission(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_id('Permissions_permissions_text').send_keys(self.perm1.permission_name)
        b.find_element_by_id('Permissions').submit()
        delete_and_confirm(b, '//td[preceding-sibling::td/text()="%s"]'
                % self.perm1.permission_name, 'Remove')
        b.find_element_by_xpath('//table[@id="group_permission_grid" and '
                'not(.//td/text()="%s")]' % self.perm1.permission_name)

    def check_notification(self, user, group, action):
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
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

    def _make_and_go_to_owner_page(self, user, group, set_owner=True):
        if set_owner:
            with session.begin():
                user_group = session.query(UserGroup). \
                    filter_by(user_id=user.user_id, group_id=group.group_id). \
                    one()
                user_group.is_owner = True
        self.browser.get(get_server_base() + 'groups/mine')
        self.browser.find_element_by_link_text(group.group_name).click()

    def test_dictionary_password_rejected(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        self._make_and_go_to_owner_page(self.user, self.group)
        e = b.find_element_by_xpath('//input[@id="Group_root_password"]')
        e.clear()
        e.send_keys(self.simple_password)
        b.find_element_by_id('Group').submit()
        error_text = b.find_element_by_xpath('//input[@name="root_password"]/'
            'following-sibling::span[contains(@class, "error")]').text
        self.assertEquals(u'Invalid password: it is based on a dictionary word',
            error_text, error_text)

    def test_set_hashed_password(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        self._make_and_go_to_owner_page(self.user, self.group)
        e = b.find_element_by_xpath('//input[@id="Group_root_password"]')
        e.clear()
        e.send_keys(self.hashed_password)
        b.find_element_by_id('Group').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            u'OK')
        self._make_and_go_to_owner_page(self.user, self.group, set_owner=False)
        new_hash = b.find_element_by_xpath('//input[@id="Group_root_password"]').get_attribute('value')
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == self.hashed_password)

    def test_set_plaintext_password(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        self._make_and_go_to_owner_page(self.user, self.group)
        e = b.find_element_by_xpath('//input[@id="Group_root_password"]')
        e.clear()
        e.send_keys(self.clear_password)
        b.find_element_by_id('Group').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            u'OK')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text(self.group.group_name).click()
        new_hash = b.find_element_by_xpath('//input[@id="Group_root_password"]').get_attribute('value')
        self.failUnless(new_hash)
        self.failUnless(crypt.crypt(self.clear_password, new_hash) == new_hash)

    def test_create_new_group(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys('Group FBZ')
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys('FBZ')
        b.find_element_by_xpath('//input[@id="Group_root_password"]'). \
            send_keys('blapppy7')
        b.find_element_by_id('Group').submit()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text('FBZ').click()
        with session.begin():
            self.assertEquals(Activity.query.filter_by(service=u'WEBUI',
                    field_name=u'Group', action=u'Added',
                    new_value=u'Group FBZ').count(), 1)
            group = Group.by_name(u'FBZ')
            self.assertEquals(group.display_name, u'Group FBZ')
            self.assert_(group.has_owner(self.user))
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].new_value, self.user.user_name)
            self.assertEquals(group.activity[-1].service, u'WEBUI')
            self.assertEquals(group.activity[-2].action, u'Added')
            self.assertEquals(group.activity[-2].field_name, u'User')
            self.assertEquals(group.activity[-2].new_value, self.user.user_name)
            self.assertEquals(group.activity[-2].service, u'WEBUI')
            self.failUnless(crypt.crypt('blapppy7', group.root_password) ==
                group.root_password, group.root_password)

    def test_create_new_group_sans_password(self):
        b = self.browser
        group_name = data_setup.unique_name('group%s')
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys(group_name)
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys(group_name)
        b.find_element_by_id('Group').submit()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text(group_name).click()
        b.find_element_by_xpath('//input[@name="root_password" and '
            'not(following-sibling::span[contains(@class, "error")])]')

    def test_can_open_edit_page_for_owned_existing_groups(self):
        with session.begin():
            data_setup.add_owner_to_group(self.user, self.group)
        b = self.browser

        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/')
        # not doing a look up using XPATH since, the group may not be on
        # the first page when run as part of the suite.
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_xpath('//input[@id="Group_root_password"]').clear()
        b.find_element_by_xpath('//input[@id="Group_root_password"]'). \
            send_keys('blapppy7')
        b.find_element_by_id('Group').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
            u'OK')
        session.expire(self.group)
        self.failUnless(crypt.crypt('blapppy7', self.group.root_password) ==
            self.group.root_password)

    def test_cannot_edit_unowned_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            user.groups.append(self.group)
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        b.find_element_by_xpath('//table[@id="group_members_grid" and not(.//text()="Remove")]')
        b.find_element_by_xpath('//body[not(.//input)]')

    def test_add_user_to_owning_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys('Group FBZ 1')
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys('FBZ-1')
        b.find_element_by_id('Group').submit()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text('FBZ-1').click()
        b.find_element_by_xpath('//input[@id="GroupUser_user_text"]').send_keys(user.user_name)
        b.find_element_by_id('GroupUser').submit()
        b.find_element_by_xpath('//td[text()="%s"]' % user.user_name)

        with session.begin():
            group = Group.by_name('FBZ-1')
        self.check_notification(user, group, action='Added')

    def test_remove_user_from_owning_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')

        group_name = data_setup.unique_name('AAAAAA%s')
        display_name = data_setup.unique_name('Group Display Name %s')

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]').send_keys(display_name)
        b.find_element_by_xpath('//input[@id="Group_group_name"]').send_keys(group_name)
        b.find_element_by_id('Group').submit()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text(group_name).click()

        # add an user
        b.find_element_by_xpath('//input[@id="GroupUser_user_text"]').send_keys(user.user_name)
        b.find_element_by_id('GroupUser').submit()

        self.mail_capture.captured_mails[:] = []

        group_id = Group.by_name(group_name).group_id
        username = user.user_name
        user_id = user.user_id

        b.find_element_by_xpath('//td[preceding-sibling::td[2]/text()="%s"]' % username)\
                .find_element_by_link_text('Remove').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          '%s Removed' % username)
        with session.begin():
            group = Group.by_name(group_name)
        self.check_notification(user, group, action='Removed')

        # remove self when I am the only owner of the group
        b.find_element_by_xpath('//td[preceding-sibling::td[2]/text()="%s"]' % self.user.user_name)\
                .find_element_by_link_text('Remove').click()
        self.assert_('Cannot remove member' in b.find_element_by_class_name('flash').text)

        # admin should be able to remove an owner, even if only one
        logout(b)
        #login back as admin
        login(b)
        b.get(get_server_base() + 'groups/edit?group_id=%s' % group_id)
        b.find_element_by_xpath('//td[preceding-sibling::td[2]/text()="%s"]' % self.user.user_name)\
                .find_element_by_link_text('Remove').click()
        self.assert_('%s Removed' % self.user.user_name in b.find_element_by_class_name('flash').text)

    #https://bugzilla.redhat.com/show_bug.cgi?id=966312
    def test_remove_self_admin_group(self):

        with session.begin():
            user = data_setup.create_admin(password='password')

        b = self.browser
        login(b, user=user.user_name, password='password')

        # admin should be in groups/mine
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('admin').click()

        # remove self
        b.find_element_by_xpath('//td[preceding-sibling::td[2]/text()="%s"]' % user.user_name)\
                .find_element_by_link_text('Remove').click()

        # admin should not be in groups/mine
        b.get(get_server_base() + 'groups/mine')
        self.assertTrue(not is_text_present(b, 'admin'))
        logout(b)

        # login as admin
        login(b)
        group = Group.by_name('admin')
        group_users = group.users
        # remove  all other users from 'admin'
        b.get(get_server_base() + 'groups/edit?group_id=1')
        for usr in group_users:
            if usr.user_id != 1:
                b.find_element_by_xpath('//td[preceding-sibling::td[2]/text()="%s"]' % usr.user_name)\
                        .find_element_by_link_text('Remove').click()

        # attempt to remove admin user
        b.find_element_by_xpath('//a[@href="removeUser?group_id=1&id=1"]').click()
        self.assert_('Cannot remove member' in b.find_element_by_class_name('flash').text)

    def test_add_user_to_admin_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            user.groups.append(Group.by_name('admin'))
            group = data_setup.create_group(group_name='aaaaaaaaaaaabcc')

        b = self.browser
        login(b, user=user.user_name, password='password')

        # admin should be in groups/mine
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('admin')

        # check if the user can edit any other group, when the user:
        # is not an owner
        # is not a member
        b.get(get_server_base() + 'groups/edit?group_id=%d' % group.group_id)
        b.find_element_by_xpath('//input[@id="Group_display_name"]')
        b.find_element_by_xpath('//input[@id="Group_group_name"]')

    def test_create_ldap_group(self):
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'groups/new')
        b.find_element_by_name('group_name').send_keys('my_ldap_group')
        b.find_element_by_name('display_name').send_keys('My LDAP group')
        self.assertEquals(b.find_element_by_name('ldap').is_selected(), False)
        b.find_element_by_name('ldap').click()
        b.find_element_by_id('Group').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        with session.begin():
            group = Group.by_name(u'my_ldap_group')
            self.assertEquals(group.ldap, True)
            self.assertEquals(group.users, [User.by_user_name(u'my_ldap_user')])

    def test_cannot_modify_membership_of_ldap_group(self):
        with session.begin():
            group = data_setup.create_group(ldap=True)
            group.users.append(data_setup.create_user())
        login(self.browser)
        b = self.browser
        b.get(get_server_base() + 'groups/edit?group_id=%s' % group.group_id)
        self.assertEquals(b.find_element_by_name('group_name').get_attribute('value'),
                group.group_name)
        # form to add new users should be absent
        b.find_element_by_xpath('//body[not(.//label[text()="User"])]')
        # "Remove" link should be absent from "User Members" table
        b.find_element_by_xpath('//table[@id="group_members_grid" and not(.//text()="Remove")]')

    def _edit_group_details(self, browser, new_group_name, new_display_name):
        b = browser
        b.find_element_by_xpath('//input[@id="Group_display_name"]').clear()
        b.find_element_by_xpath('//input[@id="Group_display_name"]').\
            send_keys(new_display_name)
        b.find_element_by_xpath('//input[@id="Group_group_name"]').clear()
        b.find_element_by_xpath('//input[@id="Group_group_name"]').\
            send_keys(new_group_name)
        b.find_element_by_id('Group').submit()

    def test_edit_display_group_names(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group = data_setup.create_group(owner=user)
            group1 = data_setup.create_group(owner=user)

        b = self.browser
        login(b, user=user.user_name, password='password')

        new_display_name = 'New Display Name for Group FBZ 2'
        new_group_name = 'FBZ-2-new'

        # edit
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text(group.group_name).click()
        self._edit_group_details(b, new_group_name, new_display_name)

        # check
        b.get(get_server_base() + "groups/edit?group_id=%d" % group.group_id)
        self.assertEquals(b.find_element_by_xpath('//input[@id="Group_display_name"]').\
                              get_attribute('value'), new_display_name)
        self.assertEquals(b.find_element_by_xpath('//input[@id="Group_group_name"]').\
                              get_attribute('value'), new_group_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=967799
    def test_edit_group_name_duplicate(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group1 = data_setup.create_group(owner=user)
            group2 = data_setup.create_group(owner=user)

        b = self.browser
        login(b, user=user.user_name, password='password')

        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text(group2.group_name).click()
        self._edit_group_details(b, group1.group_name, group2.display_name)

        flash_text = b.find_element_by_class_name('flash').text
        self.assert_('Group name already exists' in flash_text, flash_text)

    def test_cannot_rename_protected_group(self):
        with session.begin():
            admin_user = data_setup.create_admin(password='password')
            admin_group = Group.by_name(u'admin')
        b = self.browser

        login(b, user=admin_user.user_name, password='password')
        new_display_name = 'New Display Name for Group FBZ 2'
        new_group_name = 'FBZ-2-new'

        # edit
        b.get(get_server_base() + 'groups/edit?group_id=%d' % admin_group.group_id)
        self._edit_group_details(b, new_group_name, new_display_name)

        # check
        flash_text = b.find_element_by_class_name('flash').text
        self.assert_('Cannot rename protected group' in flash_text, flash_text)

    #https://bugzilla.redhat.com/show_bug.cgi?id=908174
    def test_add_remove_owner_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group = data_setup.create_group(owner=user)
            user1 = data_setup.create_user(password='password')

        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')

        # remove self (as only owner)
        b.find_element_by_link_text(group.group_name).click()
        b.find_element_by_xpath('//td[preceding-sibling::td/text()="%s"]' % user.user_name)\
                .find_element_by_link_text('Remove').click()

        flash_text = b.find_element_by_class_name('flash').text
        self.assert_("Cannot remove the only owner" in flash_text)

        # add a new user as owner
        b.find_element_by_xpath('//input[@id="GroupUser_user_text"]').send_keys(user1.user_name)
        b.find_element_by_id('GroupUser').submit()
        b.find_element_by_xpath('//td[text()="%s"]' % user1.user_name)
        b.find_element_by_xpath('//td[preceding-sibling::td/text()="%s"]' % user1.user_name)\
                .find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//td[preceding-sibling::td/text()="%s"]' % user1.user_name)\
                .find_element_by_link_text('Remove')
        logout(b)

        # login as the new user and check for ownership
        login(b, user=user1.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text(group.group_name).click()
        b.find_element_by_xpath('//input')
        with session.begin():
            self.assertEquals(Activity.query.filter_by(service=u'WEBUI',
                                                       field_name=u'Owner', action=u'Added',
                                                       new_value=user1.user_name).count(), 1)
            group = Group.by_name(group.group_name)
            self.assert_(group.has_owner(user1))
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].new_value, user1.user_name)
            self.assertEquals(group.activity[-1].service, u'WEBUI')

        # remove self as owner
        b.find_element_by_xpath('//td[preceding-sibling::td/text()="%s"]' % user1.user_name)\
                .find_element_by_link_text('Remove').click()
        b.find_element_by_xpath('//title[text()="My Groups"]')

        with session.begin():
            self.assertEquals(Activity.query.filter_by(service=u'WEBUI',
                                                       field_name=u'Owner', action=u'Removed',
                                                       old_value=user1.user_name).count(), 1)
            session.refresh(group)
            self.assertEquals(group.activity[-1].action, u'Removed')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].old_value, user1.user_name)
            self.assertEquals(group.activity[-1].service, u'WEBUI')

    #https://bugzilla.redhat.com/show_bug.cgi?id=990349
    #https://bugzilla.redhat.com/show_bug.cgi?id=990821
    def test_check_group_name_display_name_length(self):

        max_length_group_name = Group.group_name.property.columns[0].type.length
        max_length_disp_name = Group.display_name.property.columns[0].type.length

        b = self.browser
        login(b, user=self.user.user_name, password='password')

        # for new group
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys('A really long group display name'*20)
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys('areallylonggroupname'*20)
        b.find_element_by_id('Group').submit()
        error_text = b.find_element_by_xpath('//span[contains(@class, "error") '
                'and preceding-sibling::input/@name="group_name"]').text
        self.assertRegexpMatches(error_text,
                                 'Enter a value (less|not more) than %r characters long' % max_length_group_name)
        error_text = b.find_element_by_xpath('//span[contains(@class, "error") '
                'and preceding-sibling::input/@name="display_name"]').text
        self.assertRegexpMatches(error_text,
                                 'Enter a value (less|not more) than %r characters long' % max_length_disp_name)

        # modify existing group
        with session.begin():
            group = data_setup.create_group(owner=self.user)

        b.get(get_server_base() + 'groups/edit?group_id=%s' % group.group_id)
        self._edit_group_details(b, 'areallylonggroupname'*20,
                                 'A really long group display name'*20)
        error_text = b.find_element_by_xpath('//span[contains(@class, "error") '
                'and preceding-sibling::input/@name="group_name"]').text
        self.assertRegexpMatches(error_text,
                                 'Enter a value (less|not more) than %r characters long' % max_length_group_name)
        error_text = b.find_element_by_xpath('//span[contains(@class, "error") '
                'and preceding-sibling::input/@name="display_name"]').text
        self.assertRegexpMatches(error_text,
                                 'Enter a value (less|not more) than %r characters long' % max_length_disp_name)

    #https://bugzilla.redhat.com/show_bug.cgi?id=990860
    def test_show_group_owners(self):
        with session.begin():
            owner = data_setup.create_user(user_name='zzzz', password='password')
            group = data_setup.create_group(owner=owner)
            member1 = data_setup.create_user(user_name='aaaa', password='password')
            member1.groups.append(group)
            member2 = data_setup.create_user(user_name='bbbb', password='password')
            member2.groups.append(group)

        b = self.browser
        login(b, user=member1.user_name, password='password')
        b.get(get_server_base() + 'groups/edit?group_id=%d' % group.group_id)

        # the first entry should always be the owner(s)
        user_name, ownership = b.find_element_by_xpath('//table[@id="group_members_grid"]//tr[1]/td[1]').text, \
            b.find_element_by_xpath('//table[@id="group_members_grid"]//tr[1]/td[2]').text

        self.assertTrue(user_name, owner.user_name)
        self.assertTrue(ownership, 'Yes')

        user_name, ownership = b.find_element_by_xpath('//table[@id="group_members_grid"]//tr[2]/td[1]').text, \
            b.find_element_by_xpath('//table[@id="group_members_grid"]//tr[2]/td[2]').text

        self.assertTrue(user_name in [member1.user_name, member2.user_name])
        self.assertTrue(ownership, 'No')


class GroupSystemTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.group_owner = data_setup.create_user(password='password')
            self.group = data_setup.create_group()
            self.group.user_group_assocs.append(
                    UserGroup(user=self.group_owner, is_owner=True))
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=917745
    def test_add_system_to_group_twice(self):
        with session.begin():
            system = data_setup.create_system()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/edit?group_id=%s' % self.group.group_id)
        b.find_element_by_id('GroupSystem_system_text').send_keys(system.fqdn)
        b.find_element_by_xpath('//form[@id="GroupSystem"]').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        b.get(get_server_base() + 'groups/edit?group_id=%s' % self.group.group_id)
        b.find_element_by_id('GroupSystem_system_text').send_keys(system.fqdn)
        b.find_element_by_xpath('//form[@id="GroupSystem"]').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                "System '%s' is already in group '%s'" % (system.fqdn, self.group.group_name))

    # https://bugzilla.redhat.com/show_bug.cgi?id=970499
    def test_ordinary_user_cannot_add_system(self):
        with session.begin():
            system = data_setup.create_system()
        b = self.browser
        login(b, user=self.group_owner.user_name, password='password')
        b.get(get_server_base() + 'groups/edit?group_id=%s' % self.group.group_id)
        # no form to add a system
        b.find_element_by_xpath('//body[not(.//input[@id="GroupSystem_system_text"])]')
        # crafting a POST by hand should also be rejected
        cookies = dict((cookie['name'].encode('ascii', 'replace'), cookie['value'])
                for cookie in b.get_cookies())
        response = requests.post(get_server_base() + 'groups/save_system',
                cookies=cookies,
                data={'group_id': self.group.group_id, 'system.text': system.fqdn})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assert_(system not in self.group.systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=970512
    def test_remove_system(self):
        with session.begin():
            system = data_setup.create_system()
            self.group.systems.append(system)
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/edit?group_id=%s' % self.group.group_id)
        delete_and_confirm(b, '//td[preceding-sibling::td[.//text()="%s"]]' % system.fqdn,
                'Remove')
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s Removed' % system.fqdn)
        with session.begin():
            session.expire_all()
            self.assert_(system not in self.group.systems)

    def test_ordinary_group_owner_can_remove_system(self):
        with session.begin():
            system = data_setup.create_system()
            self.group.systems.append(system)
        b = self.browser
        self.assert_(self.group_owner != system.owner)
        login(b, user=self.group_owner.user_name, password='password')
        b.get(get_server_base() + 'groups/edit?group_id=%s' % self.group.group_id)
        delete_and_confirm(b, '//td[preceding-sibling::td[.//text()="%s"]]' % system.fqdn,
                'Remove')
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s Removed' % system.fqdn)
        with session.begin():
            session.expire_all()
            self.assert_(system not in self.group.systems)
