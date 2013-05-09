from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.server.webdriver_utils import login

class EditGroup(SeleniumTestCase):

    def setUp(self):
        with session.begin():
            self.perm1 = data_setup.create_permission()
            self.group = data_setup.create_group()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_add_bad_perm(self):
        sel = self.selenium
        self.login()
        sel.open('groups/edit?id=%d' % self.group.group_id)
        sel.type("Permissions_permissions_text", "dummy_perm")
        sel.submit("//form[@id='Permissions']")
        #Test that it has not been dynamically added
        self.wait_for_condition(lambda: sel.is_element_present('//span[@id="response_Permissions_failure"]'), wait_time=5)
        self.wait_for_condition(lambda: "Invalid permission value" in sel.get_text("//span[@id='response_Permissions_failure']"), wait_time=5)

        #Double check that it wasn't added to the permissions
        self.assert_("dumy_perm" not in sel.get_text("//table[@id='group_permission_grid']"))

        #Triple check it was not persisted to the DB
        sel.open('groups/edit?id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        self.assert_("dumy_perm" not in sel.get_text("//table[@id='group_permission_grid']"))

    def test_add_and_remove(self):
        sel = self.selenium
        self.login()

        sel.open('groups/edit?id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        sel.type("Permissions_permissions_text", "%s" % self.perm1.permission_name)
        sel.submit("//form[@id='Permissions']")
        #Test that permission dynamically updated
        self.wait_for_condition(lambda: self.perm1.permission_name in sel.get_text("//table[@id='group_permission_grid']"))

        #Test that the permission was persisted by reopening the current page
        sel.open('groups/edit?id=%d' % self.group.group_id)
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
        sel.open('groups/edit?id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        self.assert_(self.perm1.permission_name not in sel.get_text("//table[@id='group_permission_grid']"))

    # https://bugzilla.redhat.com/show_bug.cgi?id=917745
    def test_add_system_to_group_twice(self):
        with session.begin():
            system = data_setup.create_system()

        sel = self.selenium
        self.login()
        sel.open('')

        sel.open('groups/edit?id=%d' % self.group.group_id)
        sel.wait_for_page_to_load(30000)
        sel.type("GroupSystem_system_text", system.fqdn)
        sel.submit("//form[@id='GroupSystem']")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'), "OK")

        sel.open('groups/edit?id=%d' % self.group.group_id)
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

    def teardown(self):
        self.browser.quit()

    def test_create_new_group(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]').send_keys('Group FBZ')
        b.find_element_by_xpath('//input[@id="Group_group_name"]').send_keys('FBZ')
        b.find_element_by_xpath('//input[@value="Save"]').click()
        b.find_element_by_xpath('//h2[text()="Groups"]')
        self.assertEquals(b.title,'Groups')
        b.find_element_by_link_text('FBZ').click()
        # this is required to check whether the creator was automatically
        # added as a group owner
        self.assertEquals(b.title,'Group Edit')

    def test_can_edit_owned_existing_groups(self):
        with session.begin():
            data_setup.add_owner_to_group(self.user, self.group)
        b = self.browser

        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/')
        # not doing a look up using XPATH since, the group may not be on
        # the first page when run as part of the suite.
        b.get(get_server_base() + 'groups/edit?id=%d' % self.group.group_id)
        self.assertEquals(b.title,'Group Edit')

    def test_cannot_edit_unowned_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            user.groups.append(self.group)
        b = self.browser

        login(b, user=self.user.user_name, password='password')
        # direct URL check
        b.get(get_server_base() + 'groups/edit?id=%d' % self.group.group_id)
        flash_text = b.find_element_by_xpath('//div[@class="flash"]').text
        self.assert_('You are not an owner' in flash_text)

    def test_add_users_to_owning_group(self):
        with session.begin():
            user = data_setup.create_user(password='password')

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('Add ( + )').click()
        b.find_element_by_xpath('//input[@id="Group_display_name"]').send_keys('Group FBZ 1')
        b.find_element_by_xpath('//input[@id="Group_group_name"]').send_keys('FBZ-1')
        b.find_element_by_xpath('//input[@value="Save"]').click()
        self.assertEquals(b.title,'Groups')
        b.find_element_by_xpath('//h2[text()="Groups"]')
        b.find_element_by_link_text('FBZ-1').click()
        self.assertEquals(b.title,'Group Edit')
        b.find_element_by_xpath('//input[@id="GroupUser_user_text"]').send_keys(user.user_name)
        b.find_element_by_xpath('//input[@value="Add"]').click()
        b.find_element_by_xpath('//td[text()="%s"]' % user.user_name)
