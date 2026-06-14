# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, User
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, check_user_search_results


class UsersGridTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_search_by_username(self):
        with session.begin():
            user = data_setup.create_user()
            other_user = data_setup.create_user(user_name=u'aaardvark123')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/')
        b.find_element_by_class_name('search-query').send_keys(user.user_name)
        b.find_element_by_class_name('grid-filter').submit()
        check_user_search_results(b, present=[user], absent=[other_user])

    def test_add_duplicate_user(self):
        with session.begin():
            existing_user = data_setup.create_user(user_name=u'existing')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').send_keys(existing_user.user_name)
        modal.find_element_by_name('display_name').send_keys('anything')
        modal.find_element_by_name('email_address').send_keys(
            'anything@example.invalid')
        modal.find_element_by_tag_name('form').submit()
        self.assertIn('User %s already exists' % existing_user.user_name,
                      modal.find_element_by_class_name('alert-error').text)

    def test_adduser(self):
        user_1_name = data_setup.unique_name('anonymous%s')
        user_1_email = data_setup.unique_name('anonymous%s@my.com')
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/')
        b.find_element_by_xpath('//button[normalize-space(string(.))="Create"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').send_keys(user_1_name)
        modal.find_element_by_name('display_name').send_keys(user_1_name)
        modal.find_element_by_name('email_address').send_keys(user_1_email)
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//title[text()="%s"]' % user_1_name)


class UserTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'theuser')
        self.browser = self.get_browser()

    def test_unprivileged_view(self):
        # A regular unprivileged user will have access to see the info on
        # another user's page, but not to change anything.
        with session.begin():
            unprivileged = data_setup.create_user(password=u'unprivileged')
        b = self.browser
        login(b, user=unprivileged.user_name, password='unprivileged')
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1[contains(string(.), "%s")]' % self.user.user_name)
        b.find_element_by_xpath('//li[normalize-space(string(.))="Member of 0 groups"]')
        # no buttons or forms
        b.find_element_by_xpath('//body[not(.//form) and not(.//button)]')

    def test_user_can_reset_their_own_password(self):
        b = self.browser
        login(b, user=self.user.user_name, password='theuser')
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        password_form = b.find_element_by_xpath('//div[@class="password-reset"]//form')
        password_form.find_element_by_name('password').send_keys('newpass')
        password_form.submit()
        b.find_element_by_xpath('//h4[text()="Password has been reset"]')
        with session.begin():
            session.expire_all()
            self.assertTrue(self.user.check_password(u'newpass'))

    def test_user_can_edit_their_own_details(self):
        b = self.browser
        login(b, user=self.user.user_name, password='theuser')
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('display_name').clear()
        modal.find_element_by_name('display_name').send_keys('Bernie Sanders')
        modal.find_element_by_name('email_address').clear()
        modal.find_element_by_name('email_address').send_keys('bernie@whitehouse.gov')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath('//h1/small[normalize-space(string(.))='
                                '"Bernie Sanders <bernie@whitehouse.gov>"]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.user.display_name, u'Bernie Sanders')
            self.assertEqual(self.user.email_address, u'bernie@whitehouse.gov')

    def test_rename_user(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').clear()
        modal.find_element_by_name('user_name').send_keys(u'hclinton')
        modal.find_element_by_tag_name('form').submit()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        b.find_element_by_xpath('//title[text()="hclinton"]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.user.user_name, u'hclinton')

    def test_renaming_user_to_existing_username(self):
        with session.begin():
            other_user = data_setup.create_user()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//h1//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('user_name').clear()
        modal.find_element_by_name('user_name').send_keys(other_user.user_name)
        modal.find_element_by_tag_name('form').submit()
        self.assertIn('User %s already exists' % other_user.user_name,
                      modal.find_element_by_class_name('alert-error').text)

    def test_disable_enable(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//button[contains(text(), "Disable")]').click()
        b.find_element_by_xpath('//div[@class="alert" and text()="Account is currently disabled."]')
        with session.begin():
            session.expire_all()
            self.assertTrue(self.user.disabled)
        b.find_element_by_xpath('//button[contains(text(), "Enable")]').click()
        # Wait for the button to change back to "Disable"
        b.find_element_by_xpath('//button[contains(text(), "Disable")]')
        with session.begin():
            session.expire_all()
            self.assertFalse(self.user.disabled)

    def test_delete_undelete(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users/%s' % self.user.user_name)
        b.find_element_by_xpath('//button[contains(text(), "Delete")]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[@class="alert" and contains(text(), "Account was removed")]')
        with session.begin():
            session.expire_all()
            # Behaviour of user removal is exhaustively covered below in HTTP tests.
            self.assertIsNotNone(self.user.removed)
        b.find_element_by_xpath('//button[contains(text(), "Undelete")]').click()
        # Wait for the button to change back to "Delete"
        b.find_element_by_xpath('//button[contains(text(), "Delete")]')
        with session.begin():
            session.expire_all()
            self.assertIsNone(self.user.removed)
