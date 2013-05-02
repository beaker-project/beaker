from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup


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
        sel.open('')
        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
        sel.wait_for_page_to_load(30000)
        sel.type("Permissions_permissions_text", "dummy_perm")
        sel.submit("//form[@id='Permissions']")
        #Test that it has not been dynamically added
        self.wait_for_condition(lambda: sel.is_element_present('//span[@id="response_Permissions_failure"]'), wait_time=5)
        self.wait_for_condition(lambda: "Invalid permission value" in sel.get_text("//span[@id='response_Permissions_failure']"), wait_time=5)

        #Double check that it wasn't added to the permissions
        self.assert_("dumy_perm" not in sel.get_text("//table[@id='group_permission_grid']"))

        #Triple check it was not persisted to the DB
        sel.open('')
        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
        sel.wait_for_page_to_load(30000)
        self.assert_("dumy_perm" not in sel.get_text("//table[@id='group_permission_grid']"))

    def test_add_and_remove(self):
        sel = self.selenium
        self.login()
        sel.open('')

        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
        sel.wait_for_page_to_load(30000)
        sel.type("Permissions_permissions_text", "%s" % self.perm1.permission_name)
        sel.submit("//form[@id='Permissions']")
        #Test that permission dynamically updated
        self.wait_for_condition(lambda: self.perm1.permission_name in sel.get_text("//table[@id='group_permission_grid']"))

        #Test that the permission was persisted by reopening the current page
        sel.open('')

        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
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
        sel.open('')
        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
        sel.wait_for_page_to_load(30000)
        self.assert_(self.perm1.permission_name not in sel.get_text("//table[@id='group_permission_grid']"))

    # https://bugzilla.redhat.com/show_bug.cgi?id=917745
    def test_add_system_to_group_twice(self):
        with session.begin():
            system = data_setup.create_system()

        sel = self.selenium
        self.login()
        sel.open('')

        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
        sel.wait_for_page_to_load(30000)

        sel.type("GroupSystem_system_text", system.fqdn)
        sel.submit("//form[@id='GroupSystem']")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'), "OK")

        sel.open('')

        sel.click("//..[@id='admin']/li/a[text()='Groups']")
        sel.wait_for_page_to_load(30000)
        sel.click("link=%s" % self.group.group_name)
        sel.wait_for_page_to_load(30000)

        sel.type("GroupSystem_system_text", system.fqdn)
        sel.submit("//form[@id='GroupSystem']")
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'),
                "System '%s' is already in group '%s'" % (system.fqdn, self.group.group_name))
