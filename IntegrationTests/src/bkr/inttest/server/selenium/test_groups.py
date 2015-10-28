
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, \
        check_group_search_results, logout
from bkr.server.model import session, Group


class GroupsGridTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_can_search_by_group_name(self):
        with session.begin():
            group = data_setup.create_group()
            other_group = data_setup.create_group(
                    group_name=data_setup.unique_name(u'aardvark%s'))
        b = self.browser
        b.get(get_server_base() + 'groups/')
        b.find_element_by_class_name('search-query').send_keys(
                'group_name:"%s"' % group.group_name)
        b.find_element_by_class_name('grid-filter').submit()
        check_group_search_results(b, present=[group], absent=[other_group])

    def test_can_search_by_member_username(self):
        with session.begin():
            group = data_setup.create_group()
            member = data_setup.create_user()
            group.add_member(member)
            other_group = data_setup.create_group(
                    group_name=data_setup.unique_name(u'aardvark%s'))
        b = self.browser
        b.get(get_server_base() + 'groups/')
        b.find_element_by_class_name('search-query').send_keys(
                'member.user_name:%s' % member.user_name)
        b.find_element_by_class_name('grid-filter').submit()
        check_group_search_results(b, present=[group], absent=[other_group])

    def test_can_search_by_owner_username(self):
        with session.begin():
            group = data_setup.create_group()
            owner = data_setup.create_user()
            group.add_member(owner, is_owner=True)
            # User is a member but *not* an owner of the other group. This is 
            # to prove we really are filtering by ownership, not just 
            # membership.
            other_group = data_setup.create_group(
                    group_name=data_setup.unique_name(u'aardvark%s'))
            other_group.add_member(owner, is_owner=False)
        b = self.browser
        b.get(get_server_base() + 'groups/')
        b.find_element_by_class_name('search-query').send_keys(
                'owner.user_name:%s' % owner.user_name)
        b.find_element_by_class_name('grid-filter').submit()
        check_group_search_results(b, present=[group], absent=[other_group])

    def test_my_groups_grid_excludes_other_groups(self):
        """
        Check that the My Groups grid does not list groups which the user is 
        not a member of.
        """
        with session.begin():
            user = data_setup.create_user(password=u'password')
            my_group = data_setup.create_group()
            my_group.add_member(user)
            other_group = data_setup.create_group(
                    group_name=data_setup.unique_name(u'aardvark%s'))
        b = self.browser
        login(b, user=user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_xpath('//h1[text()="My Groups"]')
        check_group_search_results(b, present=[my_group], absent=[other_group])


class GroupCreationTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password=u'owner')
        self.browser = self.get_browser()

    def test_create_new_group(self):
        b = self.browser
        group_name = data_setup.unique_name('group%s')
        login(b, user=self.owner.user_name, password='owner')
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('group_name').send_keys(group_name)
        modal.find_element_by_name('display_name').send_keys(group_name)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//title[text()="%s"]' % group_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=990349
    def test_enforces_group_name_maximum_length(self):
        max_length = Group.group_name.property.columns[0].type.length
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('group_name').send_keys(
                'A really long group name' * 20)
        # browser just discards the extra keypresses
        self.assertEqual(max_length,
                len(modal.find_element_by_name('group_name').get_attribute('value')))

    # https://bugzilla.redhat.com/show_bug.cgi?id=990821
    def test_enforces_display_name_maximum_length(self):
        max_length = Group.display_name.property.columns[0].type.length
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('display_name').send_keys(
                'A really long group display name' * 20)
        # browser just discards the extra keypresses
        self.assertEqual(max_length,
                len(modal.find_element_by_name('display_name').get_attribute('value')))
