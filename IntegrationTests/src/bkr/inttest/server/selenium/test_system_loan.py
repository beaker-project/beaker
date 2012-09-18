
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, with_transaction, get_server_base
import unittest, time, re, os
from turbogears.database import session

class SystemLoanTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.browser = self.get_browser()
        self.system = data_setup.create_system()

    def tearDown(self):
        self.browser.quit()

    def go_to_loan_page(self):
        self.browser.get(get_server_base() + 'view/%s' % self.system.fqdn)
        self.browser.find_element_by_link_text('(Loan)').click()

    def go_to_change_loan_page(self):
        self.browser.get(get_server_base() + 'view/%s' % self.system.fqdn)
        self.browser.find_element_by_xpath('//a[.//text()=" (Change)"][preceding-sibling::a[text()=" (Return)"]]').click()

    def change_loan(self, loanee):
        self.browser.find_element_by_id("Loan_user").send_keys(loanee.user_name)
        self.browser.find_element_by_xpath(
                '//*[@id="autoCompleteResultsLoan_user"]'
                '//td[.//text()="%s"]' % loanee.user_name).click()
        self.browser.find_element_by_xpath("//input[@value='Change']").click()

    def test_can_loan_when_system_has_user(self):
        with session.begin():
            user = data_setup.create_user()
            self.system.user = user
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user)
        self.assertEqual(b.find_element_by_css_selector('.flash').text,
                "%s Loaned to %s" % (self.system.fqdn, user.user_name))

    def test_owner_can_loan_to_themself(self):
        p_word='password'
        with session.begin():
            user = data_setup.create_user(password=p_word)
            self.system.owner = user
        b = self.browser
        login(b, user=user.user_name, password=p_word)
        self.go_to_loan_page()
        self.change_loan(user)
        self.assertEqual(b.find_element_by_css_selector('.flash').text,
                "%s Loaned to %s" % (self.system.fqdn, user.user_name))

    def test_can_not_change_loan_when_system_has_loanee_and_not_admin(self):
        p_word = 'password'
        with session.begin():
            user = data_setup.create_user(password=p_word)
            self.system.user = user
            self.system.loaned = user
        b = self.browser
        login(b, user=user.user_name, password=p_word)
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        td = b.find_element_by_xpath('//td[normalize-space(preceding-sibling::th[1]/label/text())="Loaned To"]')
        self.assert_('(Change)' not in td.text, td.text)

    def test_can_change_loan_when_system_has_loanee(self):
        with session.begin():
            user = data_setup.create_user()
            user2 = data_setup.create_user()
            self.system.user = user
            self.system.loaned = user
        b = self.browser
        login(b)
        self.go_to_change_loan_page()
        self.change_loan(user2)
        self.assertEqual(b.find_element_by_css_selector('.flash').text,
                "%s Loaned to %s" % (self.system.fqdn, user2.user_name))
        with session.begin():
            session.refresh(self.system)
            reserved_activity = self.system.activity[-1]
            self.assertEqual(reserved_activity.action, 'Changed')
            self.assertEqual(reserved_activity.field_name, 'Loaned To')
            self.assertEqual(reserved_activity.old_value, user.user_name)
            self.assertEqual(reserved_activity.new_value, user2.user_name)
            self.assertEqual(reserved_activity.service, 'WEBUI')

    def test_loan_username_autocomplete_works(self):
        with session.begin():
            user = data_setup.create_user(user_name=u'distinctiveusername')
        b = self.browser
        login(b)
        self.go_to_loan_page()
        username_input = b.find_element_by_id('Loan_user')
        username_input.click()
        username_input.clear()
        username_input.send_keys('distinc')
        b.find_element_by_xpath('//*[@id="autoCompleteResultsLoan_user"]//td'
                '[.//text()="distinctiveusername"]')
