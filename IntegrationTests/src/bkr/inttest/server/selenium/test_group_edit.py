import crypt
from turbogears.database import session
from bkr.server.model import Group, User, Activity, UserGroup
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction, mail_capture
from bkr.inttest.server.webdriver_utils import login
import email

# XXX this should be assimilated by TestGroupsWD when it is converted.
class EditGroup(SeleniumTestCase):

    def setUp(self):
        with session.begin():
            self.perm1 = data_setup.create_permission()
            self.group = data_setup.create_group()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_add_bad_permission(self):
        sel = self.selenium
        self.login()
        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.type("Permissions_permissions_text", "dummy_perm")
        sel.submit("//form[@id='Permissions']")
        #Test that it has not been dynamically added
        self.wait_for_condition(lambda: sel.is_element_present('//span[@id="response_Permissions_failure"]'), wait_time=5)
        self.wait_for_condition(lambda: "Invalid permission value" in sel.get_text("//span[@id='response_Permissions_failure']"), wait_time=5)

        #Double check that it wasn't added to the permissions
        self.assert_("dumy_perm" not in sel.get_text("//table[@id='group_permission_grid']"))

        #Triple check it was not persisted to the DB
        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        self.assert_("dumy_perm" not in sel.get_text("//table[@id='group_permission_grid']"))

    def test_add_and_remove_permission(self):
        sel = self.selenium
        self.login()

        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        sel.type("Permissions_permissions_text", "%s" % self.perm1.permission_name)
        sel.submit("//form[@id='Permissions']")
        #Test that permission dynamically updated
        self.wait_for_condition(lambda: self.perm1.permission_name in sel.get_text("//table[@id='group_permission_grid']"))

        #Test that the permission was persisted by reopening the current page
        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        self.assert_(self.perm1.permission_name in sel.get_text("//table[@id='group_permission_grid']"))

        #Let's try and remove it
        sel.click("remove_permission_%s" % self.perm1.permission_id)
        self.wait_for_condition(lambda: sel.is_text_present("Are you sure you want to remove this"))
        #Click 'Yes' to remove
        sel.click("//button[normalize-space(.) = 'Yes']")
        #Check it has been removed from the table
        self.wait_for_condition(lambda: self.perm1.permission_name not in sel.get_text("//table[@id='group_permission_grid']"))

        #Reload to make sure it has been removed from the DB
        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        self.assert_(self.perm1.permission_name not in sel.get_text("//table[@id='group_permission_grid']"))

    # https://bugzilla.redhat.com/show_bug.cgi?id=917745
    def test_add_system_to_group_twice(self):
        with session.begin():
            system = data_setup.create_system()

        sel = self.selenium
        self.login()
        sel.open('')

        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        sel.type("GroupSystem_system_text", system.fqdn)
        sel.submit("//form[@id='GroupSystem']")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'), "OK")

        sel.open('groups/edit?group_id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        sel.type("GroupSystem_system_text", system.fqdn)
        sel.submit("//form[@id='GroupSystem']")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'),
                "System '%s' is already in group '%s'" % (system.fqdn, self.group.group_name))

class TestGroupsWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password='password')
            self.system = data_setup.create_system()
            self.group = data_setup.create_group()
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
        for keyword in [action, group.group_name, self.user.email_address]:
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
        b.find_element_by_xpath('//input[@value="Save"]').click()
        error_text = b.find_element_by_xpath('//input[@name="root_password"]/'
            'following-sibling::span[@class="fielderror"]').text
        self.assertEquals(u'Invalid password: it is based on a dictionary word',
            error_text, error_text)

    def test_set_hashed_password(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        self._make_and_go_to_owner_page(self.user, self.group)
        e = b.find_element_by_xpath('//input[@id="Group_root_password"]')
        e.clear()
        e.send_keys(self.hashed_password)
        b.find_element_by_xpath('//input[@value="Save"]').click()
        self.assertEquals(b.find_element_by_xpath('//div[@class="flash"]').text,
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
        b.find_element_by_xpath('//input[@value="Save"]').click()
        self.assertEquals(b.find_element_by_xpath('//div[@class="flash"]').text,
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
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys('Group FBZ')
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys('FBZ')
        b.find_element_by_xpath('//input[@id="Group_root_password"]'). \
            send_keys('blapppy7')
        b.find_element_by_xpath('//input[@value="Save"]').click()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text('F').click()
        b.find_element_by_link_text('FBZ').click()
        # this is required to check whether the creator was automatically
        # added as a group owner
        b.find_element_by_xpath('//title[normalize-space(text()) = '
            '"Group Edit"]')
        with session.begin():
            self.assertEquals(Activity.query.filter_by(service=u'WEBUI',
                    field_name=u'Group', action=u'Added',
                    new_value=u'Group FBZ').count(), 1)
            group = Group.by_name(u'FBZ')
            self.assertEquals(group.display_name, u'Group FBZ')
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
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys(group_name)
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys(group_name)
        b.find_element_by_xpath('//input[@value="Save"]').click()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text(group_name[0].upper())
        b.find_element_by_link_text(group_name).click()
        # this is required to check whether the creator was automatically
        # added as a group owner
        b.find_element_by_xpath('//title[normalize-space(text()) = '
            '"Group Edit"]')
        b.find_element_by_xpath('//input[@name="root_password" and '
            'not(following-sibling::span[@class="fielderror"])]')

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
        b.find_element_by_xpath('//input[@value="Save"]').click()
        self.assertEquals(b.find_element_by_xpath('//div[@class="flash"]').text,
            u'OK')
        session.expire(self.group)
        self.failUnless(crypt.crypt('blapppy7', self.group.root_password) ==
            self.group.root_password)

    def test_cannot_open_edit_page_for_unowned_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            user.groups.append(self.group)
        b = self.browser

        login(b, user=self.user.user_name, password='password')
        # direct URL check
        b.get(get_server_base() + 'groups/edit?group_id=%d' % self.group.group_id)
        flash_text = b.find_element_by_xpath('//div[@class="flash"]').text
        self.assert_('You are not an owner' in flash_text)

    def test_add_user_to_owning_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]'). \
            send_keys('Group FBZ 1')
        b.find_element_by_xpath('//input[@id="Group_group_name"]'). \
            send_keys('FBZ-1')
        b.find_element_by_xpath('//input[@value="Save"]').click()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text('F').click()
        b.find_element_by_link_text('FBZ-1').click()
        b.find_element_by_xpath('//input[@id="GroupUser_user_text"]').send_keys(user.user_name)
        b.find_element_by_xpath('//input[@value="Add"]').click()
        b.find_element_by_xpath('//td[text()="%s"]' % user.user_name)

        with session.begin():
            group = Group.by_name('FBZ-1')
        self.check_notification(user, group, action='Added')

    def test_remove_user_from_owning_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')

        group_name = data_setup.unique_name('Group1234%s')
        display_name = data_setup.unique_name('Group Display Name %s')

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]').send_keys(display_name)
        b.find_element_by_xpath('//input[@id="Group_group_name"]').send_keys(group_name)
        b.find_element_by_xpath('//input[@value="Save"]').click()
        b.find_element_by_xpath('//title[text()="My Groups"]')
        b.find_element_by_link_text(group_name[0].upper()).click()
        b.find_element_by_link_text(group_name).click()

        # add an user
        b.find_element_by_xpath('//input[@id="GroupUser_user_text"]').send_keys(user.user_name)
        b.find_element_by_xpath('//input[@value="Add"]').click()

        self.mail_capture.captured_mails[:] = []

        group_id = Group.by_name(group_name).group_id
        username = user.user_name
        user_id = user.user_id
        b.find_element_by_xpath('//td/a[text()="Remove (-)" and ../preceding-sibling::td[text()="%s"]]' % username).click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          '%s Removed' % username)

        with session.begin():
            group = Group.by_name(group_name)
        self.check_notification(user, group, action='Removed')

        # remove self when I am the only owner of the group
        b.find_element_by_xpath('//a[@href="removeUser?group_id=%d&id=%d"]'
                                % (group_id, self.user.user_id)).click()
        self.assert_('Cannot remove' in b.find_element_by_class_name('flash').text)

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
        b.find_element_by_xpath('//title[normalize-space(text())="Group Edit"]')
        b.find_element_by_xpath('//input[not(@id="Group_user_text")]')

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
        b.find_element_by_xpath('//table[thead/tr/th[1]/text()="User Members"]'
                '/tbody/tr[not(.//a[text()="Remove (-)"])]')

    def _edit_group_details(self, browser, new_group_name, new_display_name):
        b = browser
        b.find_element_by_xpath('//input[@id="Group_display_name"]').clear()
        b.find_element_by_xpath('//input[@id="Group_display_name"]').\
            send_keys(new_display_name)
        b.find_element_by_xpath('//input[@id="Group_group_name"]').clear()
        b.find_element_by_xpath('//input[@id="Group_group_name"]').\
            send_keys(new_group_name)
        b.find_element_by_xpath('//input[@value="Save"]').click()

    def test_edit_display_group_names(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group = data_setup.create_group(owner=user)

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
        flash_text = b.find_element_by_xpath('//div[@class="flash"]').text
        self.assert_('Cannot rename protected group' in flash_text, flash_text)
