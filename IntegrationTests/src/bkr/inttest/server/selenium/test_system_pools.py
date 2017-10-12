
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from bkr.server.model import session, SystemAccessPolicy, SystemPermission, \
        Group, SystemPool, User, Activity
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, \
check_pool_search_results, BootstrapSelect, find_policy_checkbox,\
check_policy_row_is_dirty, check_policy_row_is_not_dirty, \
check_policy_row_is_absent, click_menu_item
from bkr.inttest.server.requests_utils import put_json, post_json, patch_json
from bkr.inttest.server.requests_utils import login as send_login
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
        b.find_element_by_xpath('//title[text()="inflatable"]')
        with session.begin():
            pool = SystemPool.by_name(u'inflatable')
            self.assertEquals(pool.owner, User.by_user_name(data_setup.ADMIN_USER))

    def test_empty_pool_name_triggers_validation(self):
        """Adding a pool with an empty name triggers a validation error."""
        with session.begin():
            system_pools_count = session.query(SystemPool).count()

        b = self.browser
        login(b)
        b.get(get_server_base() + 'pools/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]')\
            .click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_tag_name('form').submit()

        self.assertTrue(modal.find_element_by_css_selector('input[name="name"]:required:invalid'))
        with session.begin():
            self.assertEqual(system_pools_count, session.query(SystemPool).count())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1203981
    def test_mine_pools(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            pool = data_setup.create_system_pool(owning_user=user)
            other_pool = data_setup.create_system_pool()
        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'pools/')
        click_menu_item(b, 'Hello, %s' % user.user_name, 'My System Pools')
        check_pool_search_results(b, present=[pool], absent=[other_pool])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1209736
    def test_pool_with_closing_script_tag_in_description(self):
        # Actually this bug affects many other things besides just the pools 
        # grid, but this is a convenient place to test for it.
        with session.begin():
            pool = data_setup.create_system_pool(
                    description=u'I am haxxing you lolz. </script>HAX')
            other_pool = data_setup.create_system_pool()
        b = self.browser
        b.get(get_server_base() + 'pools/')
        b.find_element_by_class_name('search-query').send_keys(
                'name:"%s"' % pool.name)
        b.find_element_by_class_name('grid-filter').submit()
        check_pool_search_results(b, present=[pool], absent=[other_pool])

class SystemPoolEditTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user()
            self.pool = data_setup.create_system_pool(owning_user=self.user,
                    description=u'Systems for *doing* things.\n\nhttp://pool.com')
        self.browser = self.get_browser()

    def go_to_pool_edit(self, system_pool=None, tab=None):
        if system_pool is None:
            system_pool = self.pool
        b = self.browser
        b.get(get_server_base() + system_pool.href)
        b.find_element_by_xpath('//title[normalize-space(text())="%s"]' % \
            system_pool.name)
        if tab:
            b.find_element_by_xpath('//ul[contains(@class, "system-pool-nav")]'
                    '//a[text()="%s"]' % tab).click()

    def test_edit_button_is_absent_when_not_logged_in(self):
        b = self.browser
        self.go_to_pool_edit()
        b.find_element_by_xpath('//div[@id="system-pool-info" and '
                'not(.//button[normalize-space(string(.))="Edit"])]')

    def delete_pool(self, pool=None):
        if pool is None:
            pool = self.pool
        b = self.browser
        login(b)
        self.go_to_pool_edit(pool)
        b.find_element_by_xpath('//button[contains(string(.), "Delete")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
                'delete this pool?"]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        # once it's deleted we are returned to the pools grid
        b.find_element_by_xpath('.//title[text()="Pools"]')
        with session.begin():
            self.assertEquals(SystemPool.query.filter(
                    SystemPool.name == pool.name).count(), 0)

    def test_delete_pool(self):
        self.delete_pool()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206011
    def test_can_delete_pool_with_uri_chars_in_name(self):
        with session.begin():
            pool = data_setup.create_system_pool(name=u'$@$#@!')
        self.delete_pool(pool)

    def test_delete_non_existing_pool(self):
        with session.begin():
            pool = data_setup.create_system_pool()
        b = self.browser
        login(b)
        self.go_to_pool_edit(pool)
        session.delete(pool)
        session.flush()
        b.find_element_by_xpath('//button[contains(string(.), "Delete")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
                'delete this pool?"]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-error") and '
                'h4/text()="Failed to delete" and '
                'contains(string(.), "System pool %s does not exist")]' % pool.name)

    def test_page_info_display(self):
        self.go_to_pool_edit()
        b = self.browser
        pool_info = b.find_element_by_id('system-pool-info')
        # name
        pool_info.find_element_by_xpath('.//h1[normalize-space(text())="%s"]' % \
                                           self.pool.name)
        # owner
        pool_info.find_element_by_xpath('.//h1/small[contains(text(), %s)]' % \
                                   self.pool.owner.display_name)
        # description (rendered as Markdown)
        pool_info.find_element_by_xpath(
                './/p[string(.)="Systems for doing things." and em/text()="doing"]')
        pool_info.find_element_by_xpath(
                './/p/a[@href="http://pool.com" and text()="http://pool.com"]')

    def test_update_pool(self):
        with session.begin():
            pool = data_setup.create_system_pool()
            group = data_setup.create_group()
        b = self.browser
        login(b)
        self.go_to_pool_edit(system_pool=pool)
        b.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('description').clear()
        modal.find_element_by_name('description').send_keys('newdescription')
        BootstrapSelect(modal.find_element_by_name('owner_type'))\
            .select_by_visible_text('Group')
        modal.find_element_by_name('group_name').clear()
        modal.find_element_by_name('group_name').send_keys(group.group_name)
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.refresh(pool)
            self.assertEqual(pool.description, 'newdescription')
            self.assertEqual(pool.owner, group)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1254381
    def test_cannot_update_with_empty_name(self):
        """Verifies that the pool cannot be updated with an empty name."""
        self.assertTrue(self.pool.name, "Cannot run test with empty pool name in fixture")

        b = self.browser
        login(b)
        self.go_to_pool_edit(system_pool=self.pool)
        b.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()

        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('name').clear()
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        self.assertTrue(modal.find_element_by_css_selector('input[name="name"]:required:invalid'))

        # verify that the pool's name is not modified and the name not empty due
        # to the validation error
        with session.begin():
            session.refresh(self.pool)
            self.assertTrue(self.pool.name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1364311
    def test_link_to_system_page_works(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            system.pools.append(pool)
        b = self.browser
        login(b)
        self.go_to_pool_edit(system_pool=pool, tab='Systems')
        link = b.find_element_by_xpath('//div[@id="systems"]'
                                       '/div/ul[@class="list-group pool-systems-list"]'
                                       '/li/a')
        link.click()
        b.find_element_by_xpath('//h1[text()="%s"]' % system.fqdn)

    def test_add_system(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
        b = self.browser
        login(b)
        self.go_to_pool_edit(system_pool=pool, tab='Systems')
        b.find_element_by_name('system').send_keys(system.fqdn)
        b.find_element_by_class_name('pool-add-system-form').submit()
        self.assertEquals(b.find_element_by_xpath('//div[@id="systems"]'
                                                  '/div/ul[@class="list-group pool-systems-list"]'
                                                  '/li/a').text, system.fqdn)
        with session.begin():
            session.refresh(pool)
            self.assertIn(system, pool.systems)

    def test_remove_system(self):
        with session.begin():
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            pool.systems.append(system)
        b = self.browser
        login(b)
        self.go_to_pool_edit(system_pool=pool, tab='Systems')
        b.find_element_by_link_text(system.fqdn)
        # remove
        b.find_element_by_xpath('//li[contains(a/text(), "%s")]/button' % system.fqdn).click()
        b.find_element_by_xpath('//div[@id="systems" and '
                                'not(./div/ul/li)]')
        with session.begin():
            session.refresh(pool)
            self.assertNotIn(system, pool.systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1213203
    def test_remove_system_button_is_absent_when_not_logged_in(self):
        b = self.browser
        self.go_to_pool_edit()
        b.find_element_by_xpath('//div[@id="systems" and '
                'not(.//button[normalize-space(string(.))="Remove"])]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1217283
    def test_secret_system(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system()
            pool = data_setup.create_system_pool()
            pool.systems.append(system)
            system.active_access_policy = pool.access_policy
        b = self.browser
        login(b)
        self.go_to_pool_edit(system_pool=pool, tab='System Access Policy')
        pane = b.find_element_by_id('access-policy')
        find_policy_checkbox(b, 'Everybody', 'View').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        logout(b)
        self.go_to_pool_edit(system_pool=pool, tab='Systems')
        b.find_element_by_xpath('//div[@id="systems" and '
                                'not(.//a/text()="%s")]' % system.fqdn)
        b.find_element_by_xpath('//li/em[contains(text(), "system with restricted visibility")]')
        login(b, user.user_name, password='password')
        self.go_to_pool_edit(system_pool=pool, tab='Systems')
        # user has no access to see the system
        b.find_element_by_xpath('//li/em[contains(text(), "system with restricted visibility")]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1251294
    def test_cancel_deleting_pool(self):
        b = self.browser
        login(b)
        self.go_to_pool_edit()
        b.find_element_by_xpath('//button[contains(string(.), "Delete")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
               'delete this pool?"]')
        modal.find_element_by_xpath('.//button[text()="Cancel"]').click()
        # test if the bootbox is closed properly
        b.find_element_by_xpath('//div[not(contains(@class, "modal"))]')


class SystemPoolAccessPolicyWebUITest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.pool_owner = data_setup.create_user(password='owner')
            self.pool = data_setup.create_system_pool(owning_user=self.pool_owner)
            # create an assortment of different rules
            p = self.pool.access_policy
            p.add_rule(permission=SystemPermission.edit_system,
                    group=data_setup.create_group(group_name=u'pdetectives'))
            p.add_rule(permission=SystemPermission.loan_self,
                    group=data_setup.create_group(group_name=u'psidekicks'))
            p.add_rule(permission=SystemPermission.loan_self,
                    group=data_setup.create_group(group_name=u'test?123#1234'))
            p.add_rule(permission=SystemPermission.control_system,
                    user=data_setup.create_user(user_name=u'anotherpoirot',
                                                password='testing'))
            p.add_rule(permission=SystemPermission.loan_any,
                    user=data_setup.create_user(user_name=u'anotherhastings'))
            p.add_rule(permission=SystemPermission.reserve, everybody=True)
        self.browser = self.get_browser()

    def check_checkboxes(self):
        b = self.browser
        pane = self.browser.find_element_by_id('access-policy')
        # corresponds to the rules added in setUp
        pane.find_element_by_xpath('.//table/tbody[1]/tr[1]/th[text()="Group"]')
        self.assertTrue(find_policy_checkbox(b, 'pdetectives', 'Edit system details') \
                    .is_selected())
        self.assertTrue(find_policy_checkbox(b, 'psidekicks', 'Loan to self').is_selected())
        pane.find_element_by_xpath('.//table/tbody[2]/tr[1]/th[text()="User"]')
        self.assertTrue(find_policy_checkbox(b, 'anotherpoirot', 'Control power').is_selected())
        self.assertTrue(find_policy_checkbox(b, 'anotherhastings', 'Loan to anyone').is_selected())
        self.assertTrue(find_policy_checkbox(b, 'Everybody', 'Reserve').is_selected())

    def go_to_pool_edit(self, pool=None):
        if pool is None:
            pool = self.pool
        b = self.browser
        b.get(get_server_base() + 'pools/%s/' % pool.name)

    def test_read_only_view(self):
        b = self.browser
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        self.check_checkboxes()
        # in read-only view, all checkboxes should be disabled
        # and user/group inputs should be absent
        pane = b.find_element_by_id('access-policy')
        for checkbox in pane.find_elements_by_xpath('.//input[@type="checkbox"]'):
            self.assertFalse(checkbox.is_enabled(),
                    '%s should be disabled' % checkbox.get_attribute('id'))
        pane.find_element_by_xpath('.//table[not(.//input[@type="text"])]')

    def test_owner_view(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        self.check_checkboxes()

    def test_add_rule(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()

        # grant loan_any permission to anotherpoirot user
        pane = b.find_element_by_id('access-policy')
        checkbox = find_policy_checkbox(b, 'anotherpoirot', 'Loan to anyone')
        self.assertFalse(checkbox.is_selected())
        checkbox.click()
        check_policy_row_is_dirty(b, 'anotherpoirot')
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        check_policy_row_is_not_dirty(b, 'anotherpoirot')

        # refresh to check it is persisted
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        self.assertTrue(find_policy_checkbox(b, 'anotherpoirot', 'Loan to anyone').is_selected())

    def test_remove_rule(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()

        # revoke loan_self permission from psidekicks group
        pane = b.find_element_by_id('access-policy')
        checkbox = find_policy_checkbox(b, 'psidekicks', 'Loan to self')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        check_policy_row_is_dirty(b, 'psidekicks')
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        # "psidekicks" row is completely absent now due to having no permissions
        check_policy_row_is_absent(b, 'psidekicks')

        # refresh to check it is persisted
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        self.assertNotIn('psidekicks', pane.text)

    def test_add_rule_for_new_user(self):
        with session.begin():
            data_setup.create_user(user_name=u'marple')
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()

        # grant edit_policy permission to marple user
        pane = b.find_element_by_id('access-policy')
        pane.find_element_by_xpath('.//input[@placeholder="Username"]')\
            .send_keys('marple\n')
        find_policy_checkbox(b, 'marple', 'Edit this policy').click()
        check_policy_row_is_dirty(b, 'marple')
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        check_policy_row_is_not_dirty(b, 'marple')

        # refresh to check it has been persisted
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        self.assertTrue(find_policy_checkbox(b, 'marple', 'Edit this policy').is_selected())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1076322
    def test_group_not_in_cache(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # type the group name before it exists
        with session.begin():
            self.assertEquals(Group.query.filter_by(group_name=u'anotherbeatles').first(), None)
        group_input = pane.find_element_by_xpath('.//input[@placeholder="Group name"]')
        group_input.send_keys('anotherbeatles')
        # group is created
        with session.begin():
            data_setup.create_group(group_name=u'anotherbeatles')
        # type it again
        group_input.clear()
        group_input.send_keys('anotherbeatles')
        # suggestion should appear
        pane.find_element_by_xpath('.//div[@class="tt-suggestion" and '
                'contains(string(.), "anotherbeatles")]')
        group_input.send_keys('\n')
        find_policy_checkbox(b, 'anotherbeatles', 'Edit this policy')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1073767
    # https://bugzilla.redhat.com/show_bug.cgi?id=1085028
    def test_click_group_name(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        pane.find_element_by_link_text('test?123#1234').click()
        b.find_element_by_xpath('//title[normalize-space(text())="test?123#1234"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1086506
    def test_add_rule_for_nonexistent_user(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()

        pane = b.find_element_by_id('access-policy')
        pane.find_element_by_xpath('.//input[@placeholder="Username"]')\
            .send_keys('this_user_does_not_exist\n')
        find_policy_checkbox(b, 'this_user_does_not_exist', 'Edit this policy').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and '
            'contains(string(.), "No such user")]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1160513
    def test_empty_policy(self):
        with session.begin():
            self.pool.access_policy.rules[:] = []
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        find_policy_checkbox(b, 'Everybody', 'View')
        for checkbox in pane.find_elements_by_xpath('.//input[@type="checkbox"]'):
            self.assertFalse(checkbox.is_selected())

    def test_remove_self_edit_policy_permission(self):
        b = self.browser
        login(b, user=self.pool_owner.user_name, password='owner')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # grant anotherpoirot edit_policy permission
        find_policy_checkbox(b, 'anotherpoirot', 'Edit this policy').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        logout(b)
        login(b, user='anotherpoirot', password='testing')
        self.go_to_pool_edit()
        b.find_element_by_link_text('System Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # remove self edit_policy permission
        find_policy_checkbox(b, 'anotherpoirot', 'Edit this policy').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        # the widget should be readonly
        pane.find_element_by_xpath('.//table[not(.//input[@type="checkbox" and not(@disabled)])]')
        pane.find_element_by_xpath('.//table[not(.//input[@type="text"])]')


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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1498374
    def test_cannot_create_system_pool_owned_by_deleted_user(self):
        with session.begin():
            self.owner.removed = datetime.datetime.utcnow()
        s = requests.Session()
        send_login(s)
        response = post_json(get_server_base() + 'pools/', session=s,
                data={'name': 'asdf', 'owner': {'user_name': self.owner.user_name}})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text,
                'System pool cannot be owned by deleted user %s' % self.owner.user_name)

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

    def test_cannot_update_system_pool_with_empty_name(self):
        """Verify that updating a system pool with an empty name returns an error."""
        self.assertTrue(self.pool.name, "Cannot run test with empty pool name in fixture")

        s = requests.Session()
        send_login(s, self.owner, 'theowner')
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
        send_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'pools/%s/' % self.pool.name,
                session=s, data={'owner': {'user_name': self.user.user_name}})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text,
                'System pool cannot be owned by deleted user %s' % self.user.user_name)

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
            pool.access_policy.add_rule(user=self.user,
                                        permission=SystemPermission.edit_system)
            system.active_access_policy = pool.access_policy

        self.assertIn(system, pool.systems)
        self.assertTrue(system.active_access_policy.grants
                        (self.user, SystemPermission.edit_system))

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
            self.assertEquals(system.activity[-2].field_name, 'Pool')
            self.assertEquals(system.activity[-2].action, 'Removed')
            self.assertEquals(system.activity[-2].old_value, unicode(pool))
            self.assertEquals(system.activity[-1].field_name, 'Active Access Policy')
            self.assertEquals(system.activity[-1].action, 'Changed')
            self.assertEquals(system.activity[-1].old_value, 'Pool policy: %s' % unicode(pool))
            self.assertEquals(system.activity[-1].new_value, 'Custom access policy')

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_add_deleted_user_to_access_policy(self):
        with session.begin():
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
            bad_rule = {'user': deleted_user.user_name, 'permission': 'edit'}
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.owner.user_name,
                'password': 'theowner'}).raise_for_status()
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
