from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, with_transaction, get_server_base
from bkr.server.model import Provision, ProvisionFamily, ProvisionFamilyUpdate

class OSVersionsTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.distro_tree = data_setup.create_distro(osmajor='LinuxLinux1.1')
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=860870
    def test_displayalphaos(self):
        b = self.browser
        b.get(get_server_base() + 'osversions')
        b.find_element_by_link_text('L').click()
        self.assert_(b.find_elements_by_link_text('LinuxLinux1.1'))
