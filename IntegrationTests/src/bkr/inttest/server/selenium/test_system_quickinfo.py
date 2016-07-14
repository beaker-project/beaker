
"""
Test cases for the "quick info" boxes at the top of the system page.
"""

from bkr.server.model import session, SystemPermission, SystemStatus
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login

class SystemQuickUsageTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def go_to_system_view(self, system):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_xpath('//title[normalize-space(text())="%s"]'
                % system.fqdn)

    def test_shows_currently_running_recipe(self):
        b = self.browser
        login(b)
        with session.begin():
            job = data_setup.create_running_job()
            recipe = job.recipesets[0].recipes[0]
        self.go_to_system_view(recipe.resource.system)
        usage = b.find_element_by_class_name('system-quick-usage')
        usage.find_element_by_xpath('.//span[@class="label" and text()="Reserved"]')
        usage.find_element_by_xpath('.//a[text()="%s"]' % recipe.t_id)

    def test_shows_current_loan(self):
        b = self.browser
        login(b)
        with session.begin():
            system = data_setup.create_system()
            system.loaned = data_setup.create_user()
        self.go_to_system_view(system)
        usage = b.find_element_by_class_name('system-quick-usage')
        usage.find_element_by_xpath('.//span[contains(@class, "label") and text()="Loaned"]')
        usage.find_element_by_xpath('.//a[text()="%s"]' % system.loaned.user_name)

    def action_button_labels(self):
        usage = self.browser.find_element_by_class_name('system-quick-usage')
        return [e.text.strip() for e in usage.find_elements_by_class_name('btn')]

    def test_action_buttons(self):
        """ Check that the right action buttons appear in the right circumstances. """
        with session.begin():
            user = data_setup.create_user(password=u'asdflol')
            no_access = data_setup.create_system(shared=False)
            lc1 = data_setup.create_labcontroller()
            borrowable = data_setup.create_system(lab_controller=lc1)
            borrowable.custom_access_policy.add_rule(
                    SystemPermission.loan_self, user=user)
            borrowable_but_loaned = data_setup.create_system()
            borrowable_but_loaned.loaned = data_setup.create_user()
            borrowable_but_loaned.custom_access_policy.add_rule(
                    SystemPermission.loan_self, user=user)
            borrowed = data_setup.create_system()
            borrowed.loaned = user
            # "stealable" means loaned to someone else but you have perms to return their loan
            stealable = data_setup.create_system()
            stealable.loaned = data_setup.create_user()
            stealable.custom_access_policy.add_rule(
                    SystemPermission.loan_any, user=user)
            manual = data_setup.create_system(status=SystemStatus.manual, shared=True)
            taken = data_setup.create_system(status=SystemStatus.manual, shared=True)
            taken.reserve_manually(user=user, service=u'testdata')
        login(self.browser, user=user.user_name, password='asdflol')
        self.go_to_system_view(no_access)
        self.assertEquals(self.action_button_labels(), ['Request Loan'])
        self.go_to_system_view(borrowable_but_loaned)
        self.assertEquals(self.action_button_labels(), ['Schedule Reservation'])
        self.go_to_system_view(borrowable)
        self.assertEquals(self.action_button_labels(), ['Borrow'])
        self.go_to_system_view(borrowed)
        self.assertEquals(self.action_button_labels(), ['Take', 'Return Loan'])
        self.go_to_system_view(stealable)
        self.assertEquals(self.action_button_labels(), ['Return Loan'])
        self.go_to_system_view(manual)
        self.assertEquals(self.action_button_labels(), ['Take'])
        self.go_to_system_view(taken)
        self.assertEquals(self.action_button_labels(), ['Return'])
