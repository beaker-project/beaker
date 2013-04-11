import unittest
from selenium.webdriver.support.ui import WebDriverWait
from bkr.server.model import SystemActivity, System
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout
from bkr.inttest import data_setup, with_transaction, get_server_base
from turbogears.database import session

class SystemLoanTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.browser = self.get_browser()
        self.system = data_setup.create_system()

    def tearDown(self):
        self.browser.quit()

    def go_to_loan_page(self):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('(Loan Settings)').click()

    def change_loan(self, loanee, comment=None):
        b = self.browser
        WebDriverWait(b,5).until(lambda driver: driver. \
            find_element_by_name("update_loan.loaned").is_displayed() is True)
        loan_field = b.find_element_by_name("update_loan.loaned")
        loan_field.clear()
        loan_field.send_keys(loanee)
        if comment:
            comment_field = b.find_element_by_name("update_loan.loan_comment")
            comment_field.clear()
            comment_field.send_keys(comment)
        b.find_element_by_name("update_loan.update").click()

    def verify_loan_update(self, user):
        b = self.browser
        b.find_element_by_xpath('//span[@id="loanee-name" and '
            'normalize-space(text())="%s"]' % user)

    def test_return_loan(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        # Login as admin, loan to average Joe,
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        logout(b)

        # Login as average Joe, and click 'Return Loan'
        login(b, user.user_name, 'password')
        self.go_to_loan_page()
        b.find_element_by_name('update_loan.return').click()
        self.verify_loan_update('')
        logout(b)

        # Login as admin, loan to self and add comment
        login(b)
        comment = u'As I pee, sir, I see Pisa!'
        self.go_to_loan_page()
        self.change_loan(u'admin', comment)
        self.verify_loan_update(u'admin')
        sys = self.system
        # Test going from '' -> comment in SystemActivity
        sys_activity_comment = sys.dyn_activity.filter(SystemActivity.field_name == \
            u'Loan Comment').first()
        self.assertEqual(sys_activity_comment.old_value, u'')
        self.assertEqual(sys_activity_comment.new_value, comment)
        # Let's clear the user field
        b.find_element_by_name('update_loan.loaned').clear()
        b.find_element_by_name('update_loan.update').click()
        # This is equivalent to a loan return
        b.find_element_by_xpath('//textarea[@name='
            '"update_loan.loan_comment" and normalize-space(text())=""]')
        # Test going from 'admin' -> '' in SystemActivity
        sys = System.by_fqdn(self.system.fqdn, user)
        sys_activity_name = sys.dyn_activity.filter(SystemActivity.field_name == \
            u'Loaned To').first()
        self.assertEqual(sys_activity_name.old_value, u'admin')
        self.assertEqual(sys_activity_name.new_value, u'')
        # Test going from comment -> '' in SystemActivity
        sys_activity_comment2 = sys.dyn_activity.filter(SystemActivity.field_name == \
            u'Loan Comment').first()
        self.assertEqual(sys_activity_comment2.old_value, comment)
        self.assertEqual(sys_activity_comment2.new_value, u'')

    def test_ajax_loan_change_is_persisted(self):
        with session.begin():
            user = data_setup.create_user()
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        self.verify_loan_update(user.user_name)
        # Reload page
        self.go_to_loan_page()
        self.assertEqual(b.find_element_by_id('loanee-name').text,
            user.user_name)
        loaned_to = b.find_element_by_name('update_loan.loaned'). \
            get_attribute('value')
        self.assertEqual(user.user_name, loaned_to)
        # Test going from '' -> user in SystemActivity
        sys = self.system
        sys_activity = sys.dyn_activity.filter(SystemActivity.field_name ==
            u'Loaned To').first()
        self.assertEqual(sys_activity.old_value, u'')
        self.assertEqual(sys_activity.new_value, user.user_name)

    def test_can_add_comments_with_loanee(self):
        with session.begin():
            user = data_setup.create_user()
        b = self.browser
        login(b)
        self.go_to_loan_page()
        comment = 'Murder for a jar of red rum'
        self.change_loan(user.user_name, comment)
        self.verify_loan_update(user.user_name)
        # Reload page
        self.go_to_loan_page()
        loan_comment = b.find_element_by_name('update_loan.loan_comment').text
        self.assertEqual(comment, loan_comment)


    def test_can_loan_when_system_has_user(self):
        with session.begin():
            user = data_setup.create_user()
            self.system.user = user
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        self.verify_loan_update(user.user_name)

    def test_owner_can_loan_to_themself(self):
        p_word='password'
        with session.begin():
            user = data_setup.create_user(password=p_word)
            self.system.owner = user
        b = self.browser
        login(b, user=user.user_name, password=p_word)
        self.go_to_loan_page()
        self.change_loan(user.user_name)
        self.verify_loan_update(user.user_name)

    def test_can_not_change_loan_when_system_has_loanee_and_not_admin(self):
        p_word = 'password'
        with session.begin():
            user = data_setup.create_user(password=p_word)
            self.system.user = user
            self.system.loaned = user
        b = self.browser
        login(b, user=user.user_name, password=p_word)
        self.go_to_loan_page()
        loan_action = b.find_element_by_id('update_loan').text
        self.assertTrue('Loan to' not in loan_action)

    def test_can_change_loan_when_system_has_loanee(self):
        with session.begin():
            user = data_setup.create_user()
            user2 = data_setup.create_user()
            self.system.user = user
            self.system.loaned = user
        b = self.browser
        login(b)
        self.go_to_loan_page()
        self.change_loan(user2.user_name)
        self.verify_loan_update(user2.user_name)

        with session.begin():
            session.refresh(self.system)
            reserved_activity = self.system.activity[-1]
            self.assertEqual(reserved_activity.action, 'Changed')
            self.assertEqual(reserved_activity.field_name, 'Loaned To')
            self.assertEqual(reserved_activity.old_value, user.user_name)
            self.assertEqual(reserved_activity.new_value, user2.user_name)
            self.assertEqual(reserved_activity.service, 'WEBUI')
