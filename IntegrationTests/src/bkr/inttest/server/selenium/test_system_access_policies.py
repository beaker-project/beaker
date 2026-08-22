
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, SystemAccessPolicy, SystemPermission, \
        Group
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, \
    find_policy_checkbox, check_policy_row_is_dirty, \
    check_policy_row_is_not_dirty, check_policy_row_is_absent
from selenium.webdriver.support.ui import Select

class SystemAccessPolicyWebUITest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.system_owner = data_setup.create_user(password='owner')
            self.system = data_setup.create_system(owner=self.system_owner,
                    shared=False)
            # create an assortment of different rules
            p = self.system.custom_access_policy
            p.add_rule(permission=SystemPermission.edit_system,
                    group=data_setup.create_group(group_name=u'detectives'))
            p.add_rule(permission=SystemPermission.loan_self,
                    group=data_setup.create_group(group_name=u'sidekicks'))
            p.add_rule(permission=SystemPermission.loan_self,
                    group=data_setup.create_group(group_name=u'test?123#123'))
            p.add_rule(permission=SystemPermission.control_system,
                    user=data_setup.create_user(user_name=u'poirot', password=u'testing'))
            p.add_rule(permission=SystemPermission.loan_any,
                    user=data_setup.create_user(user_name=u'hastings'))
            p.add_rule(permission=SystemPermission.reserve, everybody=True)
        self.browser = self.get_browser()

    def check_checkboxes(self):
        b = self.browser
        pane = self.browser.find_element_by_id('access-policy')
        # corresponds to the rules added in setUp
        pane.find_element_by_xpath('.//table/tbody[1]/tr[1]/th[text()="Group"]')
        self.assertTrue(find_policy_checkbox(b, 'detectives', 'Edit system details') \
                        .is_selected())
        self.assertTrue(find_policy_checkbox(b, 'sidekicks', 'Loan to self').is_selected())
        pane.find_element_by_xpath('.//table/tbody[2]/tr[1]/th[text()="User"]')
        self.assertTrue(find_policy_checkbox(b, 'poirot', 'Control power').is_selected())
        self.assertTrue(find_policy_checkbox(b, 'hastings', 'Loan to anyone').is_selected())
        self.assertTrue(find_policy_checkbox(b, 'Everybody', 'Reserve').is_selected())

    def test_read_only_view(self):
        b = self.browser
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
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
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        self.check_checkboxes()

    def test_add_rule(self):
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()

        # grant loan_any permission to poirot user
        pane = b.find_element_by_id('access-policy')
        checkbox = find_policy_checkbox(b, 'poirot', 'Loan to anyone')
        self.assertFalse(checkbox.is_selected())
        checkbox.click()
        check_policy_row_is_dirty(b, 'poirot')
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        check_policy_row_is_not_dirty(b, 'poirot')

        # refresh to check it is persisted
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        self.assertTrue(find_policy_checkbox(b, 'poirot', 'Loan to anyone').is_selected())

    def test_remove_rule(self):
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        # revoke loan_self permission from sidekicks group
        pane = b.find_element_by_id('access-policy')
        checkbox = find_policy_checkbox(b, 'sidekicks', 'Loan to self')
        self.assertTrue(checkbox.is_selected())
        checkbox.click()
        check_policy_row_is_dirty(b, 'sidekicks')
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        # "sidekicks" row is completely absent now due to having no permissions
        check_policy_row_is_absent(b, 'sidekicks')

        # refresh to check it is persisted
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        self.assertNotIn('sidekicks', pane.text)

    def test_add_rule_for_new_user(self):
        with session.begin():
            data_setup.create_user(user_name=u'marple')
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()

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
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        self.assertTrue(find_policy_checkbox(b, 'marple', 'Edit this policy').is_selected())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1076322
    def test_group_not_in_cache(self):
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # type the group name before it exists
        with session.begin():
            self.assertEqual(Group.query.filter_by(group_name=u'beatles').first(), None)
        group_input = pane.find_element_by_xpath('.//input[@placeholder="Group name"]')
        group_input.send_keys('beatles')
        # group is created
        with session.begin():
            data_setup.create_group(group_name=u'beatles')
        # type it again
        group_input.clear()
        group_input.send_keys('beatles')
        # suggestion should appear
        pane.find_element_by_xpath('.//div[@class="tt-suggestion" and '
                'contains(string(.), "beatles")]')
        group_input.send_keys('\n')
        find_policy_checkbox(b, 'beatles', 'Edit this policy')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1073767
    # https://bugzilla.redhat.com/show_bug.cgi?id=1085028
    def test_click_group_name(self):
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        pane.find_element_by_link_text('test?123#123').click()
        b.find_element_by_xpath('//title[normalize-space(text())="test?123#123"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1086506
    def test_add_rule_for_nonexistent_user(self):
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()

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
            self.system.custom_access_policy.rules[:] = []
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        find_policy_checkbox(b, 'Everybody', 'View')
        for checkbox in pane.find_elements_by_xpath('.//input[@type="checkbox"]'):
            self.assertFalse(checkbox.is_selected())

    def test_remove_self_edit_policy_permission(self):
        b = self.browser
        login(b, user=self.system_owner.user_name, password='owner')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # grant poirot edit_policy permission
        find_policy_checkbox(b, 'poirot', 'Edit this policy').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        logout(b)
        login(b, user='poirot', password='testing')
        b.get(get_server_base() + 'view/%s/' % self.system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')

        # remove self edit_policy permission
        find_policy_checkbox(b, 'poirot', 'Edit this policy').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        # the widget should be readonly
        pane.find_element_by_xpath('.//table[not(.//input[@type="checkbox" and not(@disabled)])]')
        pane.find_element_by_xpath('.//table[not(.//input[@type="text"])]')

    def test_active_access_policy_selection(self):
        with session.begin():
            user = data_setup.create_user()
            owner = data_setup.create_user(password='password')
            system = data_setup.create_system(owner=owner)
            data_setup.create_system_pool(systems=[system])
            pool2 = data_setup.create_system_pool(systems=[system])
            pool2.access_policy.add_rule(user=user,
                                         permission=SystemPermission.edit_system)
        b = self.browser
        login(b, owner.user_name, password='password')
        b.get(get_server_base() + 'view/%s/' % system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # Currently the system is using its custom access policy
        self.assertTrue(pane.find_element_by_xpath(
            '//label[contains(string(.), "Use custom access policy")]'
            '/input[@type="radio"]').is_selected())

        # change to pool policy
        pane.find_element_by_xpath(
                           '//label[contains(string(.), "Use policy from pool:")]'
                           '/input[@type="radio"]').click()
        Select(pane.find_element_by_name('pool_name')).select_by_visible_text(pool2.name)
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        # wait for the request to complete
        pane.find_element_by_xpath('.//span[@class="sync-status" and not(node())]')
        # check if the policy change has persisted
        b.get(get_server_base() + 'view/%s/' % system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        self.assertTrue(b.find_element_by_xpath(
                                        '//label[contains(string(.), "Use policy from pool:")]'
                                        '/input[@type="radio"]').is_selected())
        selected_options = Select(b.find_element_by_name('pool_name')).\
                           all_selected_options
        self.assertTrue(len(selected_options), 1)
        self.assertEqual(selected_options[0].text, pool2.name)
        self.assertFalse(b.find_element_by_xpath(
                                         '//label[contains(string(.), "Use custom access policy")]'
                                         '/input[@type="radio"]').is_selected())
        with session.begin():
            session.expire_all()
            self.assertTrue(system.active_access_policy.grants(user,
                                                   SystemPermission.edit_system))
        logout(b)
        # no change allowed when not logged in/no right privileges
        b.get(get_server_base() + 'view/%s/' % system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        self.assertFalse(b.find_element_by_xpath(
                                         '//label[contains(string(.), "Use policy from pool:")]'
                                         '/input[@type="radio"]').is_enabled())
        selected_options = Select(b.find_element_by_name('pool_name')). \
                           all_selected_options
        self.assertEqual(selected_options[0].text, pool2.name)
        self.assertFalse(b.find_element_by_xpath(
            '//label[contains(string(.), "Use custom access policy")]'
            '/input[@type="radio"]').is_enabled())

    def test_give_away_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            owner = data_setup.create_user(password='password')
            system = data_setup.create_system(owner=owner)
            pool = data_setup.create_system_pool(systems=[system])
            pool.access_policy.add_rule(user=user,
                                        permission=SystemPermission.edit_policy)
            system.active_access_policy = pool.access_policy
        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'view/%s/' % system.fqdn)
        b.find_element_by_link_text('Access Policy').click()
        pane = b.find_element_by_id('access-policy')
        # Currently the system is using a pool access policy
        self.assertTrue(pane.find_element_by_xpath(
            '//label[contains(string(.), "Use policy from pool:")]'
            '/input[@type="radio"]').is_selected())
        # change to custom access policy
        pane.find_element_by_xpath(
                           '//label[contains(string(.), "Use custom access policy")]'
                           '/input[@type="radio"]').click()
        pane.find_element_by_xpath('.//button[text()="Save changes"]').click()
        pane.find_element_by_xpath('//div[@id="access-policy" and not (.//div[@class="form-actions"])]')
        self.assertTrue(pane.find_element_by_xpath(
            '//label[contains(string(.), "Use custom access policy")]'
            '/input[@type="radio"]').is_selected())
        # The radio buttons should be read only
        self.assertFalse(b.find_element_by_xpath(
            '//label[contains(string(.), "Use policy from pool:")]'
            '/input[@type="radio"]').is_enabled())
        self.assertFalse(b.find_element_by_xpath(
            '//label[contains(string(.), "Use custom access policy")]'
            '/input[@type="radio"]').is_enabled())
