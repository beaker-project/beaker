
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present, \
    delete_and_confirm, logout
from bkr.server.model import session, SystemPermission, SystemAccessPolicy


class TestGroups(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password='password')
            self.system = data_setup.create_system()
            self.group = data_setup.create_group()
            self.user.groups.append(self.group)
            self.system.groups.append(self.group)
            self.rand_group = data_setup.create_group \
                (group_name=data_setup.unique_name(u'aardvark%s'))

        session.flush()
        self.browser = self.get_browser()

    def teardown(self):
        self.browser.quit()

    def test_group_remove(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath("//input[@name='group.text']").clear()
        b.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b.find_element_by_id('Search').submit()
        delete_and_confirm(b, "//tr[td/a[normalize-space(text())='%s']]" %
            self.group.group_name, delete_text='Delete Group')
        self.assertEqual(
            b.find_element_by_class_name('flash').text,
            '%s deleted' % self.group.display_name)

    def test_group_remove_on_different_pages(self):
        b1 = self.browser
        b2 = self.get_browser()
        login(b1)
        login(b2)
        b1.get(get_server_base() + 'groups/')
        b1.find_element_by_xpath("//input[@name='group.text']").clear()
        b1.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b1.find_element_by_id('Search').submit()

        b2.get(get_server_base() + 'groups/')
        b2.find_element_by_xpath("//input[@name='group.text']").clear()
        b2.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b2.find_element_by_id('Search').submit()

        delete_and_confirm(b1, "//tr[td/a[normalize-space(text())='%s']]" %
            self.group.group_name, delete_text='Delete Group')
        self.assertEqual(
            b1.find_element_by_class_name('flash').text,
            '%s deleted' % self.group.display_name)

        delete_and_confirm(b2, "//tr[td/a[normalize-space(text())='%s']]" %
            self.group.group_name, delete_text='Delete Group')
        self.assertEqual(
            b2.find_element_by_class_name('flash').text,
            'Invalid group or already removed')

    #https://bugzilla.redhat.com/show_bug.cgi?id=968843
    def test_group_has_submitted_job_remove(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group = data_setup.create_group(owner=user)
            job = data_setup.create_job(owner=user, group=group)

        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        delete_and_confirm(b, "//td[preceding-sibling::td/a[normalize-space(text())='%s']]/form" % \
                               group.group_name, delete_text='Delete Group')

        flash_text = b.find_element_by_class_name('flash').text
        self.assert_('Cannot delete a group which has associated jobs' in flash_text, flash_text)

    def test_group(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_xpath('//h1[text()="My Groups"]')
        self.assert_(not is_text_present(b, self.rand_group.group_name))
        b.find_element_by_link_text('System count: 1').click()
        self.assert_(is_text_present(b, 'Systems in Group %s' % self.group.group_name))
        self.assert_(is_text_present(b, self.system.fqdn))

    #https://bugzilla.redhat.com/show_bug.cgi?id=968865
    def test_group_remove_link_visibility(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            user.groups.append(self.group)
            group = data_setup.create_group(owner=user)

        b = self.browser
        #login as admin
        login(b)
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath("//input[@name='group.text']").clear()
        b.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b.find_element_by_id('Search').submit()
        self.assert_('Delete' in b.find_element_by_xpath("//tr[(td[1]/a[text()='%s'])]"
                                                             % self.group.group_name).text)
        logout(b)

        # login as another user
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath("//input[@name='group.text']").clear()
        b.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b.find_element_by_id('Search').submit()
        self.assert_('Delete' not in b.find_element_by_xpath("//tr[(td[1]/a[text()='%s'])]"
                                                                 % self.group.group_name).text)
        b.find_element_by_xpath("//input[@name='group.text']").clear()
        b.find_element_by_xpath("//input[@name='group.text']").send_keys(group.group_name)
        b.find_element_by_id('Search').submit()
        self.assert_('Delete' in b.find_element_by_xpath("//tr[(td[1]/a[text()='%s'])]"
                                                                 % group.group_name).text)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1085703
    def test_group_has_access_policy_rule_remove(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            system = data_setup.create_system(owner=user,
                                                   shared=False)
            system.custom_access_policy = SystemAccessPolicy()
            group = data_setup.create_group(owner=user)
            p = system.custom_access_policy
            p.add_rule(permission=SystemPermission.edit_system,
                       group=group)

        b = self.browser
        login(b, user=user.user_name, password='password')

        # check current rules
        self.assertEquals(len(p.rules), 1)
        self.assert_(p.rules[0].user is None)
        self.assertEquals(p.rules[0].group, group)

        # delete the group
        b.get(get_server_base() + 'groups/mine')
        delete_and_confirm(b, "//tr[td/a[normalize-space(text())='%s']]" %
                           group.group_name, delete_text='Delete Group')
        self.assertEqual(
            b.find_element_by_class_name('flash').text,
            '%s deleted' % group.display_name)

        # check if the access policy rule has been removed
        session.refresh(p)
        self.assertEquals(len(p.rules), 0)
