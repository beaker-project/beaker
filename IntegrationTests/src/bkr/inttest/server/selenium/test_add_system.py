
from selenium.webdriver.support.ui import Select
from bkr.server.model import session, System, SystemPermission
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base

class AddSystem(WebDriverTestCase):
    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def tearDown(self):
        self.browser.quit()

    def test_add_system(self):
        fqdn = u'test-system-1'
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys(fqdn)
        b.find_element_by_xpath('//button[text()="Add"]').click()
        # should go to system page
        b.find_element_by_xpath('//h1[text()="%s"]' % fqdn)

    def test_cannot_add_existing_system(self):
        with session.begin():
            data_setup.create_system(fqdn=u'preexisting-system')
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys('preexisting-system')
        b.find_element_by_xpath('//button[text()="Add"]').click()
        # this is not ideal...
        b.find_element_by_xpath('''//*[text()="System with fqdn u'preexisting-system' already exists"]''')

    #https://bugzilla.redhat.com/show_bug.cgi?id=1021737
    def test_empty_fqdn(self):

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        # leave the fqdn field blank
        b.find_element_by_xpath('//button[text()="Add"]').click()
        # we can't actually check the HTML5 validation error,
        # but we should still be at the system modal
        b.find_element_by_css_selector('input[name=fqdn]:required')

    def test_grants_view_permission_to_everybody_by_default(self):
        fqdn = data_setup.unique_name(u'test-add-system%s.example.invalid')
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys(fqdn)
        b.find_element_by_xpath('//button[text()="Add"]').click()
        b.find_element_by_xpath('//h1[text()="%s"]' % fqdn)
        with session.begin():
            system = System.query.filter(System.fqdn == fqdn).one()
            self.assertTrue(system.custom_access_policy.grants_everybody(
                    SystemPermission.view))
