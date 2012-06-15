
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import get_server_base

class UtilisationGraphTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        b = self.browser.quit()

    def test_it(self):
        b = self.browser
        b.get(get_server_base() + 'reports/utilisation_graph')
        self.assertEquals(b.title, 'Utilisation graph')
        # TODO test the data shown in the graph
