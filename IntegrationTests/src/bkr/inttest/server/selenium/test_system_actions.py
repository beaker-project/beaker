import email
from turbogears.database import session
from selenium.common.exceptions import NoSuchElementException
from bkr.inttest.server.selenium import WebDriverTestCase, SeleniumTestCase
from bkr.inttest.server.webdriver_utils import get_server_base, login, logout
from bkr.inttest.mail_capture import MailCaptureThread
from bkr.inttest import data_setup

class SystemAction(WebDriverTestCase):

    @classmethod
    def setupClass(cls):
        with session.begin():
            cls.browser = cls.get_browser()
            cls.owner_email_address = data_setup.unique_name(u'picard%s@starfleet.gov')
            cls.system_owner = data_setup.create_user(
                email_address=cls.owner_email_address)
            cls.system_fqdn = data_setup.unique_name('ncc1701d%s')
            cls.system = data_setup.create_system(fqdn=cls.system_fqdn,
                owner=cls.system_owner)
            cls.lc_name = data_setup.unique_name(u'testing_for_mail%s')
            lc = data_setup.create_labcontroller(cls.lc_name)
            cls.system.lab_controller = lc
            lender = u'amd'
            location = u'bne'
            vendor = u'intel'
            cls.system.lender = lender
            cls.system.location = location
            cls.system.vendor = vendor
            cls.reporter_email_address = data_setup.unique_name(u'crusher%s@starfleet.gov')
            cls.problem_reporter = data_setup.create_user(password=u'password',
                display_name=data_setup.unique_name('Crusher Lady%s'),
                email_address=cls.reporter_email_address)

    @classmethod
    def teardownClass(cls):
        cls.browser.quit()

    def setUp(self):
        b = self.browser
        try:
            login(b, user=self.problem_reporter.user_name, password='password')
        except NoSuchElementException:
            pass #Already logged in

        self.mail_capture = MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()

    def _std_check_mail(self, sender, rcpts, raw_msg, notification, payload, subject,
        system=None, reporter=None):
        if not system:
            system = self.system
        if not reporter:
            reporter = self.problem_reporter
        self.assertEqual(rcpts, [system.owner.email_address,
                reporter.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['From'],
                r'"%s \(via Beaker\)" <%s>' % (reporter.display_name, reporter.email_address ))
        self.assertEqual(msg['To'], '%s' % system.owner.email_address)
        self.assertEqual(msg['Subject'], '%s' % subject)
        self.assertEqual(msg['Cc'], reporter.email_address)
        self.assertEqual(msg['X-Beaker-Notification'], notification)
        self.assertEqual(msg['X-Lender'], system.lender)
        self.assertEqual(msg['X-Owner'], system.owner.user_name)
        self.assertEqual(msg['X-Location'], system.location)
        self.assertEqual(msg['X-Lab-Controller'], system.lab_controller.fqdn)
        self.assertEqual(msg['X-Vendor'], system.vendor)
        self.assertEqual(msg['X-Type'], system.type.value)
        # This will break with multiple arched system...
        self.assertEqual(msg['X-Arch'], system.arch[0].arch)
        self.assertEqual(msg.get_payload(decode=True),payload)

    def test_anonymous_cant_contact_owner(self):
        b = self.browser
        logout(b)
        # Test can't access when not logged in
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        self.assertRaises(NoSuchElementException,lambda: b.find_element_by_link_text('(Contact Owner)'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=652334
    def test_system_activity_entry_is_correctly_truncated(self):
        with session.begin():
            system = data_setup.create_system()
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('(Contact Owner)').click()
        b.find_element_by_xpath('//button[.//text()=\'Report Problem\']').click()
        b.find_element_by_name('problem.description').send_keys(u'a' + u'\u044f' * 100)
        b.find_element_by_xpath('//input[@value=\'Report\']').click()
        # Wait for our success box
        SeleniumTestCase.wait_and_try(lambda: b.find_element_by_xpath('//div/span[text()=\'Success\']'))

    def test_reporter_and_system_cc_list_are_cced(self):
        with session.begin():
            interested_party_email = data_setup.unique_name(u'%sinterestedparty1@example.invalid')
            system = data_setup.create_system()
            system.cc = [interested_party_email]
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('(Contact Owner)').click()
        b.find_element_by_xpath('//button[.//text()=\'Report Problem\']').click()
        b.find_element_by_name('problem.description').send_keys('I broke it')
        b.find_element_by_xpath('//input[@value=\'Report\']').click()
        SeleniumTestCase.wait_and_try(lambda: b.find_element_by_xpath('//div/span[text()=\'Success\']'))
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        self.assertEqual(rcpts, [system.owner.email_address,
                self.problem_reporter.email_address, interested_party_email])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['Cc'], '%s, %s' % (self.problem_reporter.email_address,
                interested_party_email))

    def test_report_problem_via_job_and_recipe(self):
        with session.begin():
            owner = data_setup.create_user()
            job = data_setup.create_completed_job(owner=owner)
        # Completing a job creates an email which we don't need
        self.mail_capture.captured_mails[:] = []
        b = self.browser
        b.get(get_server_base() + 'jobs/%s' % job.id)
        b.find_element_by_link_text('Report Problem with system').click()
        b.find_element_by_id('problem_description').send_keys('I broke it')
        b.find_element_by_xpath('//input[@value=\'Report\']').click()
        SeleniumTestCase.wait_and_try(lambda: b.find_element_by_xpath('//div/span[text()=\'Success\']'))
        self.assertEqual(len(self.mail_capture.captured_mails), 1)

        self.mail_capture.captured_mails[:] = []
        b.get(get_server_base() + 'recipes/%s' % job.recipesets[0].recipes[0].id)
        b.find_element_by_link_text('Report Problem with system').click()
        b.find_element_by_id('problem_description').send_keys('I broke it')
        b.find_element_by_xpath('//input[@value=\'Report\']').click()
        SeleniumTestCase.wait_and_try(lambda: b.find_element_by_xpath('//div/span[text()=\'Success\']'))
        self.assertEqual(len(self.mail_capture.captured_mails), 1)

    def test_report_problem(self):
        b = self.browser

        # Test can send problem report succesfully
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('(Contact Owner)').click()
        b.find_element_by_xpath('//button[.//text()=\'Report Problem\']').click()
        b.find_element_by_name('problem.description').send_keys('testing problem')
        b.find_element_by_xpath('//input[@value=\'Report\']').click()
        # Wait for our success box
        SeleniumTestCase.wait_and_try(lambda: b.find_element_by_xpath('//div/span[text()=\'Success\']'))
        # Check the email was sent
        SeleniumTestCase.wait_and_try(lambda: self.assertEqual(len(self.mail_capture.captured_mails), 1))
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        payload = 'A Beaker user has reported a problem with system \n' \
            '%s <%sview/%s>.\n\n' \
            'Reported by: %s\n\n' \
            'Problem description:\n' \
            'testing problem' \
            % (self.system_fqdn, get_server_base(), self.system_fqdn,
                self.problem_reporter.display_name)
        self._std_check_mail(sender, rcpts, raw_msg, 'system-problem',
            payload, 'Problem reported for %s' % self.system.fqdn)

    def test_loan_request(self):
        b = self.browser

        # Test can send loan request succesfully
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('(Contact Owner)').click()
        b.find_element_by_xpath('//button[.//text()=\'Request Loan\']').click()
        b.find_element_by_name('loan.message').send_keys('request loan')
        b.find_element_by_xpath('//input[@value=\'Request\']').click()
        # Wait for our success box
        SeleniumTestCase.wait_and_try(lambda: b.find_element_by_xpath('//div/span[text()=\'Success\']'))
        # Check the email was sent
        SeleniumTestCase.wait_and_try(lambda: self.assertEqual(len(self.mail_capture.captured_mails), 1))
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        payload = 'A Beaker user has requested you loan them the system\n' \
            '%s <%sview/%s>.\n' \
            'Here is a copy of their request:\n' \
            'request loan\n Requested by: %s' \
            % (self.system_fqdn, get_server_base(), self.system_fqdn,
                self.problem_reporter.display_name)
        self._std_check_mail(sender, rcpts, raw_msg, 'loan-request',
            payload, 'Loan request for %s' % self.system.fqdn)
