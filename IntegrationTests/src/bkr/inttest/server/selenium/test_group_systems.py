from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present


class TestGroupSystems(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password='password')
            self.system = data_setup.create_system()
            self.group = data_setup.create_group()
            self.user.groups.append(self.group)
            self.system.groups.append(self.group)
        session.flush()
        self.browser = self.get_browser()

    def teardown(self):
        self.browser.quit()

    def test_group(self):
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'groups/mine')
        b.find_element_by_link_text('System count: 1').click()
        self.assert_(is_text_present(b, 'Systems for group %s' % self.group.group_name))
        self.assert_(is_text_present(b, self.system.fqdn))
