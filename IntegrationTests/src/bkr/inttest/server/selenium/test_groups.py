
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present, \
    logout
from bkr.server.model import session


class TestGroups(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password='password')
            self.system = data_setup.create_system()
            self.group = data_setup.create_group()
            self.user.groups.append(self.group)
            self.rand_group = data_setup.create_group \
                (group_name=data_setup.unique_name(u'aardvark%s'))

        session.flush()
        self.browser = self.get_browser()

    def test_group(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_xpath('//h1[text()="My Groups"]')
        self.assert_(not is_text_present(b, self.rand_group.group_name))
