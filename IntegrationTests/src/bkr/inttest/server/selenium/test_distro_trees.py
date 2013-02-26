import urlparse
import requests
from datetime import datetime, timedelta
from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, delete_and_confirm, \
        wait_for_animation
from bkr.inttest import data_setup, get_server_base, with_transaction
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

    def test_labcontroller(self):
        # Add
        with session.begin():
            lc = data_setup.create_labcontroller(fqdn=data_setup. \
                                                 unique_name(u'lc%s'))
            distro_tree = data_setup.create_distro_tree()
        b = self.browser
        login(b)
        go_to_distro_tree_view(b, distro_tree)
        b.find_element_by_xpath("//select[@id='lab_controller_id']/"
            "option[normalize-space(text())='%s']" % lc.fqdn).click()
        b.find_element_by_xpath("//input[@id='url']"). \
            send_keys('http://blah.com')
        b.find_element_by_link_text('Add ( + )').click()
        # A trailing '/' is added automatically if it's not present. RHBZ#912242
        self.assertEqual(
            b.find_element_by_xpath('//div[@class="flash"]').text,
            'Added %s http://blah.com/' % lc.fqdn)

        # Delete
        delete_and_confirm(b, "//td[preceding-sibling::td/a[@href='http://blah.com/']]/form", delete_text='Delete ( - )')
        self.assertEqual(
            b.find_element_by_xpath('//div[@class="flash"]').text,
            'Deleted %s http://blah.com/' % lc.fqdn)

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=811404
    def test_yum_repo_config(self):
        b = self.browser
        login(b)
        go_to_distro_tree_view(b, self.distro_tree)
        b.find_element_by_link_text('Repos').click()
        repo_link = b.find_element_by_css_selector('table.yum_config a')
        self.assert_(repo_link.text.endswith('.repo'))
        response = requests.get(
                urlparse.urljoin(b.current_url, repo_link.get_attribute('href')))
        response.raise_for_status()
        self.assert_('text/plain' in response.headers['Content-Type'])
        self.assert_('baseurl=' in response.text, response.text)

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=839820
    def test_xml_filter(self):
        with session.begin():
            distro_trees_in = [
                data_setup.create_distro_tree(distro_tags=[u'MYTAG1']),
                data_setup.create_distro_tree(distro_tags=[u'MYTAG2']),
            ]
            distro_tree_out = data_setup.create_distro_tree(distro_tags=[u'MYTAG3'])
        distro_trees = self.server.distrotrees.filter({'xml': '''
            <or>
                <distro_tag value="MYTAG1" />
                <distro_tag value="MYTAG2" />
            </or>
            '''})
        returned_ids = set(dt['distro_tree_id'] for dt in distro_trees)
        self.assertEquals(returned_ids, set(dt.id for dt in distro_trees_in))

class DistroTreeSearch(WebDriverTestCase):

    def tearDown(self):
        self.browser.quit()

    @classmethod
    @with_transaction
    def setupClass(cls):
        data_setup.create_labcontroller()
        cls.distro_one_name = data_setup.unique_name(u'nametest%s')
        cls.distro_one_osmajor = u'osmajortest1'
        cls.distro_one_osminor = u'1'
        cls.distro_one_variant = u'myvariant'
        cls.distro_one_tag = [u'MYTAG']

        cls.distro_one = data_setup.create_distro(name=cls.distro_one_name,
            osmajor=cls.distro_one_osmajor, osminor = cls.distro_one_osminor,
            tags =cls.distro_one_tag)
        cls.distro_tree_one = data_setup.create_distro_tree(distro=cls.distro_one,
            variant=cls.distro_one_variant)
        # Two days in the future
        cls.distro_two_name = data_setup.unique_name(u'nametest%s')
        cls.distro_two_osmajor = u'osmajortest2'
        cls.distro_two_osminor = u'2'

        cls.distro_two = data_setup.create_distro(name=cls.distro_two_name,
            osmajor=cls.distro_two_osmajor, osminor = cls.distro_two_osminor,)
        cls.distro_tree_two = data_setup.create_distro_tree(distro=cls.distro_two)
        cls.distro_tree_two.date_created = datetime.utcnow() + timedelta(days=2)

        cls.distro_three_name = data_setup.unique_name(u'nametest%s')
        cls.distro_three_osmajor = u'osmajortest3'
        cls.distro_three_osminor = u'3'

        cls.distro_three = data_setup.create_distro(name=cls.distro_three_name,
            osmajor=cls.distro_three_osmajor, osminor = cls.distro_three_osminor,)
        cls.distro_tree_three = data_setup.create_distro_tree(distro=cls.distro_three)

    def setUp(self):
        self.browser = self.get_browser()

    def check_search_results(self, present, absent):
        for distro_tree in absent:
            self.browser.find_element_by_xpath('//table[@id="widget" and '
                    'not(.//td[1]/a/text()="%s")]' % distro_tree.id)
        for distro_tree in present:
            self.browser.find_element_by_xpath('//table[@id="widget" and '
                    './/td[1]/a/text()="%s"]' % distro_tree.id)

    def test_search_by_name(self):
        b = self.browser
        b.get(get_server_base() + 'distrotrees')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='search_0_table']/"
            "option[@value='Name']").click()
        b.find_element_by_xpath("//select[@id='search_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="search_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="search_0_value"]'). \
            send_keys('%s' % self.distro_three_name)
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_tree_three],
                absent=[self.distro_tree_one, self.distro_tree_two])

    def test_search_by_osmajor(self):
        b = self.browser
        b.get(get_server_base() + 'distrotrees')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='search_0_table']/"
            "option[@value='OSMajor']").click()
        b.find_element_by_xpath("//select[@id='search_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="search_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="search_0_value"]'). \
            send_keys('%s' % self.distro_one_osmajor)
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_tree_one],
                absent=[self.distro_tree_two, self.distro_tree_three])

    def test_search_by_osminor(self):
        b = self.browser
        b.get(get_server_base() + 'distrotrees')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='search_0_table']/"
            "option[@value='OSMinor']").click()
        b.find_element_by_xpath("//select[@id='search_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="search_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="search_0_value"]'). \
            send_keys('1')
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_tree_one],
                absent=[self.distro_tree_two, self.distro_tree_three])

    def test_search_by_variant(self):
        b = self.browser
        b.get(get_server_base() + 'distrotrees')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='search_0_table']/"
            "option[@value='Variant']").click()
        b.find_element_by_xpath("//select[@id='search_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath('//input[@id="search_0_value"]').clear()
        b.find_element_by_xpath('//input[@id="search_0_value"]'). \
            send_keys('%s' % self.distro_one_variant)
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_tree_one],
                absent=[self.distro_tree_two, self.distro_tree_three])

    def test_search_by_created(self):
        b = self.browser
        b.get(get_server_base() + 'distrotrees')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='search_0_table']/"
            "option[@value='Created']").click()
        b.find_element_by_xpath("//select[@id='search_0_operation']/"
            "option[@value='after']").click()
        b.find_element_by_xpath('//input[@id="search_0_value"]').clear()
        now_and_1 = datetime.utcnow() + timedelta(days=1)
        now_and_1_string = now_and_1.strftime('%Y-%m-%d')
        b.find_element_by_xpath('//input[@id="search_0_value"]'). \
            send_keys(now_and_1_string)
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_tree_two],
                absent=[self.distro_tree_one, self.distro_tree_three])

    def test_search_by_tag(self):
        b = self.browser
        b.get(get_server_base() + 'distrotrees')
        b.find_element_by_id('advancedsearch').click()
        wait_for_animation(b, '#searchform')
        b.find_element_by_xpath("//select[@id='search_0_table']/"
            "option[@value='Tag']").click()
        b.find_element_by_xpath("//select[@id='search_0_operation']/"
            "option[@value='is']").click()
        b.find_element_by_xpath("//select[@id='search_0_value']/"
            "option[@value='%s']" % self.distro_one_tag[0]).click()
        b.find_element_by_name('Search').click()
        self.check_search_results(present=[self.distro_tree_one],
                absent=[self.distro_tree_two, self.distro_tree_three])
