from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import get_server_base

class DistroFamily(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_search_is_not_there(self):
        b = self.browser
        b.get(get_server_base() + 'distrofamily/')
        b.find_element_by_xpath('//div[@class="page-header" and '
            'not(..//form[@id="Search"]//'
            'input[@name="osversion.text"])]')
