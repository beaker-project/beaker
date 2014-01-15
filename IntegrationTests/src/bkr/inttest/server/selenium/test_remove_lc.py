
from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, with_transaction, get_server_base
from turbogears.database import session
from bkr.inttest.server.webdriver_utils import login

class RemoveLabController(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.lc = data_setup.create_labcontroller(
            fqdn=data_setup.unique_name(u'%d1111'))
        self.system.lab_controller = self.lc
        self.distro_tree = data_setup.create_distro_tree(lab_controllers=[self.lc])
        self.browser = self.get_browser()
        login(self.browser)

    def tearDown(self):
        self.browser.quit()

    def test_remove_and_add(self):
        b = self.browser

        self.assert_(any(lca.lab_controller == self.lc
                for lca in self.distro_tree.lab_controller_assocs))

        #Remove
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '//a[contains(text(), "Remove")]' % self.lc.fqdn).click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s removed' % self.lc)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.lab_controller is None)
            session.refresh(self.distro_tree)
            self.assert_(not any(lca.lab_controller == self.lc
                    for lca in self.distro_tree.lab_controller_assocs))

        #Re add
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '//a[contains(text(), "Re-Add")]' % self.lc.fqdn).click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Successfully re-added %s' % self.lc)


    def test_system_page(self):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath(
                '//div[@class="control-group" and '
                    'normalize-space(string(label))="Lab Controller"]'
                '//span[normalize-space(text())="%s"]' % self.lc.fqdn)
        self.failUnless(self.system.lab_controller is self.lc)

        # Remove it
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '//a[contains(text(), "Remove")]' % self.lc.fqdn).click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s removed' % self.lc)

        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath(
                '//div[@class="control-group" and '
                    'normalize-space(string(label))="Lab Controller"]'
                '//span[not(text())]')
        with session.begin():
            session.refresh(self.system)
            self.failUnless(not self.system.lab_controller)

        # Re add it
        b.get(get_server_base() + 'labcontrollers/')
        b.find_element_by_xpath('//tr[normalize-space(string(td[1]))="%s"]'
                '//a[contains(text(), "Re-Add")]' % self.lc.fqdn).click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Successfully re-added %s' % self.lc)
        b.get(get_server_base() + 'edit/%s' % self.system.fqdn)
        Select(b.find_element_by_name('lab_controller_id'))\
            .select_by_visible_text(self.lc.fqdn)
        b.find_element_by_name('form').submit()
        b.find_element_by_xpath(
                '//div[@class="control-group" and '
                    'normalize-space(string(label))="Lab Controller"]'
                '//span[normalize-space(text())="%s"]' % self.lc.fqdn)
        with session.begin():
            session.refresh(self.system)
            self.assert_(self.system.lab_controller is self.lc)
