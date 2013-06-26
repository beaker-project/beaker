from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from bkr.server.model import session, OSMajor, Arch

def go_to_edit_osmajor(browser, osmajor_name):
    browser.get(get_server_base() + 'osversions')
    browser.find_element_by_name('osversion.text').send_keys(osmajor_name)
    browser.find_element_by_xpath('//form[@id="Search"]').submit()
    browser.find_element_by_xpath('//table[@id="widget"]/tbody/tr[1]'
            '/td[1]/a[text()="%s"]' % osmajor_name).click()

class OSVersionsTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def tearDown(self):
        self.browser.quit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=860870
    def test_displayalphaos(self):
        with session.begin():
            data_setup.create_distro(osmajor=u'LinuxLinux1.1')
        b = self.browser
        b.get(get_server_base() + 'osversions')
        b.find_element_by_link_text('L').click()
        self.assert_(b.find_elements_by_link_text('LinuxLinux1.1'))

    def test_edit_osmajor_install_options(self):
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'LinuxLinux2.1', arch=u'ia64')
            data_setup.create_distro_tree(osmajor=u'LinuxLinux2.1', arch=u'ppc64')
        b = self.browser
        # set them from scratch
        go_to_edit_osmajor(b, 'LinuxLinux2.1')
        b.find_element_by_xpath('//table[@id="install_options_all"]'
                '//td[preceding-sibling::th/text()="Kickstart Metadata"]'
                '/input').send_keys('one')
        b.find_element_by_xpath('//table[@id="install_options_all"]'
                '//td[preceding-sibling::th/text()="Kernel Options"]'
                '/input').send_keys('two')
        b.find_element_by_xpath('//table[@id="install_options_all"]'
                '//td[preceding-sibling::th/text()="Kernel Options Post"]'
                '/input').send_keys('three')
        b.find_element_by_xpath('//table[@id="install_options_ppc64"]'
                '//td[preceding-sibling::th/text()="Kickstart Metadata"]'
                '/input').send_keys('four')
        b.find_element_by_xpath('//table[@id="install_options_ppc64"]'
                '//td[preceding-sibling::th/text()="Kernel Options"]'
                '/input').send_keys('five')
        b.find_element_by_xpath('//table[@id="install_options_ppc64"]'
                '//td[preceding-sibling::th/text()="Kernel Options Post"]'
                '/input').send_keys('six')
        b.find_element_by_link_text('Save Changes').click()
        self.assertEquals(
                b.find_element_by_xpath('//div[@class="flash"]').text,
                'Install options saved for LinuxLinux2.1')
        # check everything is saved
        with session.begin():
            o = OSMajor.by_name(u'LinuxLinux2.1')
            ia64 = Arch.by_name(u'ia64')
            ppc64 = Arch.by_name(u'ppc64')
            self.assertEquals(set(o.install_options_by_arch.keys()),
                    set([None, ia64, ppc64]),
                    o.install_options_by_arch)
            self.assertEquals(o.install_options_by_arch[None].ks_meta, 'one')
            self.assertEquals(o.install_options_by_arch[None].kernel_options, 'two')
            self.assertEquals(o.install_options_by_arch[None].kernel_options_post, 'three')
            self.assertEquals(o.install_options_by_arch[ia64].ks_meta, '')
            self.assertEquals(o.install_options_by_arch[ia64].kernel_options, '')
            self.assertEquals(o.install_options_by_arch[ia64].kernel_options_post, '')
            self.assertEquals(o.install_options_by_arch[ppc64].ks_meta, 'four')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options, 'five')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options_post, 'six')
        # now edit the existing options
        go_to_edit_osmajor(b, 'LinuxLinux2.1')
        input = b.find_element_by_xpath('//table[@id="install_options_ppc64"]'
                '//td[preceding-sibling::th/text()="Kickstart Metadata"]'
                '/input')
        self.assertEquals(input.get_attribute('value'), 'four')
        input.clear()
        input.send_keys('something else')
        input = b.find_element_by_xpath('//table[@id="install_options_ppc64"]'
                '//td[preceding-sibling::th/text()="Kernel Options"]'
                '/input')
        self.assertEquals(input.get_attribute('value'), 'five')
        input.clear()
        input.send_keys('something else')
        input = b.find_element_by_xpath('//table[@id="install_options_ppc64"]'
                '//td[preceding-sibling::th/text()="Kernel Options Post"]'
                '/input')
        self.assertEquals(input.get_attribute('value'), 'six')
        input.clear()
        input.send_keys('something else')
        b.find_element_by_link_text('Save Changes').click()
        self.assertEquals(
                b.find_element_by_xpath('//div[@class="flash"]').text,
                'Install options saved for LinuxLinux2.1')
        # check they are updated
        with session.begin():
            session.expunge_all()
            o = OSMajor.by_name(u'LinuxLinux2.1')
            ppc64 = Arch.by_name(u'ppc64')
            self.assertEquals(o.install_options_by_arch[ppc64].ks_meta,
                    'something else')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options,
                    'something else')
            self.assertEquals(o.install_options_by_arch[ppc64].kernel_options_post,
                    'something else')

    #https://bugzilla.redhat.com/show_bug.cgi?id=975644
    def test_edit_osmajor_alias(self):
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'LinuxLinux2.1', arch=u'ia64')

        b = self.browser
        go_to_edit_osmajor(b, 'LinuxLinux2.1')
        b.find_element_by_xpath('//input[@id="form_alias"]').send_keys('linux21')
        b.find_element_by_xpath('//input[@value="Edit OSMajor"]').submit()
        self.assertEquals(
            b.find_element_by_xpath('//div[@class="flash"]').text,
            'Changes saved for LinuxLinux2.1')
