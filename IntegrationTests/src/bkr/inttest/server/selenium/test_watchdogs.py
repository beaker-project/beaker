
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase

class WatchdogsTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_page_works(self):
        # make sure we have at least one watchdog to see
        with session.begin():
            data_setup.mark_job_running(data_setup.create_job())
        b = self.browser
        b.get(get_server_base() + 'watchdogs/')
        self.assertEquals(b.title, 'Watchdogs')
