from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, click_menu_item
from bkr.inttest import data_setup, get_server_base

class Menu(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_my_menu(self):
        b = self.browser
        login(b)
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Jobs')
        b.find_element_by_xpath('//title[text()="My Jobs"]')
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Recipes')
        b.find_element_by_xpath('//title[text()="Recipes"]')
        click_menu_item(b, 'Hello, %s' % data_setup.ADMIN_USER, 'My Systems')
        b.find_element_by_xpath('//title[text()="My Systems"]')
