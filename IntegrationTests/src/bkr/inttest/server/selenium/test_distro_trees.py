
from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from bkr.server.model import LabControllerDistroTree

def go_to_distro_tree_view(browser, distro_tree):
    browser.get('%sdistrotrees/%s' % (get_server_base(), distro_tree.id))

class DistroTreeViewTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.distro_tree = data_setup.create_distro_tree()
            self.distro_tree.ks_meta = 'no_debug_repos'
            self.distro_tree.kernel_options = 'repo=asdf'
            self.distro_tree.kernel_options_post = 'norhgb'
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_install_options(self):
        b = self.browser
        go_to_distro_tree_view(b, self.distro_tree)
        b.find_element_by_link_text('Install Options').click()
        self.assertEqual(
            b.find_element_by_xpath('//table[@id="install_options"]'
                '//td[preceding-sibling::th[1]/text()="Kickstart Metadata"]').text,
            'no_debug_repos')
        self.assertEqual(
            b.find_element_by_xpath('//table[@id="install_options"]'
                '//td[preceding-sibling::th[1]/text()="Kernel Options"]').text,
            'repo=asdf')
        self.assertEqual(
            b.find_element_by_xpath('//table[@id="install_options"]'
                '//td[preceding-sibling::th[1]/text()="Kernel Options Post"]').text,
            'norhgb')

    def test_update_install_options(self):
        b = self.browser
        login(b)
        go_to_distro_tree_view(b, self.distro_tree)
        b.find_element_by_link_text('Install Options').click()
        b.find_element_by_link_text('Edit').click()
        b.find_element_by_name('ks_meta').click()
        b.find_element_by_name('ks_meta').clear()
        b.find_element_by_name('ks_meta').send_keys('no_addon_repos')
        b.find_element_by_name('kernel_options').click()
        b.find_element_by_name('kernel_options').clear()
        b.find_element_by_name('kernel_options').send_keys('repo=qwerty')
        b.find_element_by_name('kernel_options_post').click()
        b.find_element_by_name('kernel_options_post').clear()
        b.find_element_by_name('kernel_options_post').send_keys('rhgb')
        b.find_element_by_link_text('Save Changes').click()
        self.assertEqual(
            b.find_element_by_xpath('//div[@class="flash"]').text,
            'Updated install options')
        self.assertEqual(
            b.find_element_by_xpath('//table[@id="install_options"]'
                '//td[preceding-sibling::th[1]/text()="Kickstart Metadata"]').text,
            'no_addon_repos')
        self.assertEqual(
            b.find_element_by_xpath('//table[@id="install_options"]'
                '//td[preceding-sibling::th[1]/text()="Kernel Options"]').text,
            'repo=qwerty')
        self.assertEqual(
            b.find_element_by_xpath('//table[@id="install_options"]'
                '//td[preceding-sibling::th[1]/text()="Kernel Options Post"]').text,
            'rhgb')

class DistroTreesFilterXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    def test_filtering_by_lab_controller(self):
        with session.begin():
            good_lc = data_setup.create_labcontroller()
            bad_lc = data_setup.create_labcontroller()
            distro_tree_in = data_setup.create_distro_tree()
            distro_tree_out = data_setup.create_distro_tree()
            session.flush()
            distro_tree_in.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=good_lc, url=u'http://notimportant')]
            distro_tree_out.lab_controller_assocs[:] = [LabControllerDistroTree(
                    lab_controller=bad_lc, url=u'http://notimportant')]
        distro_trees = self.server.distrotrees.filter({'labcontroller': good_lc.fqdn})
        self.assert_(distro_tree_in.id in [d['distro_tree_id'] for d in distro_trees], distro_trees)
        self.assert_(distro_tree_out.id not in [d['distro_tree_id'] for d in distro_trees], distro_trees)
