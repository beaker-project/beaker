from turbogears.database import session
from bkr.server.model import SystemStatus
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup


class SystemReturnTest(SeleniumTestCase):

    def setUp(self):
        self.user = data_setup.create_user(password='password')
        self.system = data_setup.create_system(shared=True)
        self.lc  = data_setup.create_labcontroller(fqdn='remove_me')
        self.system.lab_controller = self.lc
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_cant_return_sneakily(self):
        self.login() #login as admin
        self.system.status = SystemStatus.by_name(u'Manual')
        session.flush()
        sel = self.selenium
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load(3000)
        sel.click('link=(Take)')
        sel.wait_for_page_to_load(3000)

        self.logout()
        self.login(user=self.user.user_name, password='password')
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load(3000)

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        sel.open('user_change?id=%s' % self.system.id)
        sel.wait_for_page_to_load("30000")
        self.assert_('You were unable to change the user for %s' % self.system.fqdn in sel.get_text('//body'))


    def test_return_with_no_lc(self):
        self.system.status = SystemStatus.manual
        session.flush()
        sel = self.selenium
        self.login(user=self.user.user_name, password='password')
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')
        sel.click('link=(Take)')
        sel.wait_for_page_to_load('30000')

        # Let's remove the LC
        self.logout()
        self.login()
        sel.open("labcontrollers/")
        sel.wait_for_page_to_load('30000')
        sel.click("//a[@onclick=\"has_watchdog('%s')\"]" % self.lc.id)
        sel.wait_for_page_to_load("30000")

        self.logout()
        self.login(user=self.user.user_name, password='password')
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')
        sel.click('link=(Return)')
        sel.wait_for_page_to_load('30000')
        text = sel.get_text('//body')
        self.assert_('Returned %s' % self.system.fqdn in text)


