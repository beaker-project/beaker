
from bkr.server.model import session, SystemPermission
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login

class SystemCommandsTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password=u'owner')
            self.privileged = data_setup.create_user(password=u'privileged')
            self.system = data_setup.create_system(owner=self.owner, shared=False,
                    lab_controller=data_setup.create_labcontroller())
            data_setup.configure_system_power(self.system)
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.control_system,
                    user=self.privileged)
            self.unprivileged = data_setup.create_user(password=u'unprivileged')
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def go_to_commands_tab(self, system):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Commands').click()

    def check_cannot_power(self, system, error_message):
        b = self.browser
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('commands')
        pane.find_element_by_xpath('.//div[contains(@class, "alert") and text()="%s."]'
                % error_message)
        # try issuing the request directly also
        b.get(get_server_base() + 'action_power?id=%s&action=on' % system.id)
        self.assertEquals(b.find_element_by_class_name('flash').text, error_message)

    def check_cannot_clear_netboot(self, system, error_message):
        b = self.browser
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('commands')
        pane.find_element_by_xpath('.//div[contains(@class, "alert") and text()="%s."]'
                % error_message)
        # try issuing the request directly also
        b.get(get_server_base() + 'systems/clear_netboot_form?fqdn=%s' % system.fqdn)
        self.assertEquals(b.find_element_by_class_name('flash').text, error_message)

    def check_power_on(self, system):
        b = self.browser
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('commands')
        pane.find_element_by_xpath('.//button[normalize-space(string(.))="Power On"]').click()
        confirmation = b.switch_to_alert()
        self.assertEquals(confirmation.text,
                'Are you sure you wish to power the system on?')
        confirmation.accept()
        confirmation = b.switch_to_alert()
        self.assertEquals(confirmation.text,
                'You are NOT the user of this machine, '
                'are you SURE you wish to power the system on?')
        confirmation.accept()
        self.assertIn('power on command enqueued',
                b.find_element_by_class_name('flash').text)
        with session.begin():
            self.assertEquals(system.command_queue[0].action, 'on')

    def check_clear_netboot(self, system):
        b = self.browser
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('commands')
        pane.find_element_by_xpath('.//button[normalize-space(string(.))="Clear Netboot"]').click()
        confirmation = b.switch_to_alert()
        self.assertEquals(confirmation.text,
                'Are you sure you wish to clear the system\'s netboot configuration?')
        confirmation.accept()
        confirmation = b.switch_to_alert()
        self.assertEquals(confirmation.text,
                'You are NOT the user of this machine, '
                'are you SURE you wish to clear the system\'s netboot configuration?')
        confirmation.accept()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Clear netboot command enqueued')
        with session.begin():
            self.assertEquals(system.command_queue[0].action, 'clear_netboot')

    def test_cannot_power_when_not_logged_in(self):
        b = self.browser
        # Same as check_cannot_power except we action_power redirects to 
        # a login form instead of showing a flash message, in this case
        self.go_to_commands_tab(self.system)
        pane = b.find_element_by_id('commands')
        pane.find_element_by_xpath('.//div[contains(@class, "alert") and '
                'text()="You are not logged in."]')
        # try issuing the request directly also
        b.get(get_server_base() + 'action_power?id=%s&action=on' % self.system.id)
        b.find_element_by_xpath('//title[text()="Login"]')

    def test_cannot_power_without_permission(self):
        login(self.browser, user=self.unprivileged.user_name, password='unprivileged')
        self.check_cannot_power(self.system,
                'You do not have permission to control this system')

    # https://bugzilla.redhat.com/show_bug.cgi?id=740321
    def test_cannot_power_system_without_lc(self):
        with session.begin():
            self.system.lab_controller = None
        login(self.browser, user=self.owner.user_name, password='owner')
        self.check_cannot_power(self.system,
                'System is not configured for power support')

    def test_power_on(self):
        login(self.browser, user=self.owner.user_name, password='owner')
        self.check_power_on(self.system)

    def test_can_power_with_permission(self):
        login(self.browser, user=self.privileged.user_name, password='privileged')
        self.check_power_on(self.system)

    def test_cannot_clear_netboot_without_permission(self):
        login(self.browser, user=self.unprivileged.user_name, password='unprivileged')
        self.check_cannot_clear_netboot(self.system,
                'You do not have permission to control this system')

    def test_clear_netboot(self):
        login(self.browser, user=self.owner.user_name, password='owner')
        self.check_clear_netboot(self.system)

    def test_can_clear_netboot_with_permission(self):
        login(self.browser, user=self.privileged.user_name, password='privileged')
        self.check_clear_netboot(self.system)
