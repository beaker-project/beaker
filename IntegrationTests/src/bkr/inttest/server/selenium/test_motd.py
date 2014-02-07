from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import get_server_base
import turbogears as tg
from lxml import etree

class TestMOTD(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_motd(self):
        f = open(tg.config.get('beaker.motd'), 'rb')
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(f,parser)
        the_motd = etree.tostring(tree, method='text')
        f.close()
        b = self.browser
        b.get(get_server_base())
        self.assertEquals(
                b.find_element_by_css_selector('.motd span').text,
                the_motd)
