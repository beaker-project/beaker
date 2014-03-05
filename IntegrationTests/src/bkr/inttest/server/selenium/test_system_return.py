
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.server.model import SystemStatus
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest import data_setup, with_transaction, get_server_base
from bkr.inttest.server.webdriver_utils import login, is_text_present


class SystemReturnTestWD(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def test_cannot_return_running_recipe(self):
        b = self.browser
        system = self.recipe.resource.system
        login(b)
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        # "Return" button should be absent
        b.find_element_by_xpath('//form[@name="form"'
                                'and not(.//a[normalize-space(string(.))="Return"])]')
        # try doing it directly
        b.get(get_server_base() + 'user_change?id=%s' % system.id)
        self.assertEquals(b.find_element_by_css_selector('.flash').text,
            "Failed to return %s: Currently running R:%s" % (system.fqdn, self.recipe.id))

    #https://bugzilla.redhat.com/show_bug.cgi?id=1007789
    def test_can_return_manual_reservation_when_automated(self):

        with session.begin():
            user = data_setup.create_user(password='foobar')
            system = data_setup.create_system(owner=user, status=SystemStatus.manual)

        b = self.browser
        login(b, user=user.user_name, password="foobar")

        # Take
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Take').click()
        self.assertEquals(b.find_element_by_css_selector('.flash').text,
                          "Reserved %s" % (system.fqdn))

        # toggle status to Automated
        with session.begin():
            system.status = SystemStatus.automated
        session.expunge_all()

        # Attempt to return
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Return').click()
        self.assertEquals(b.find_element_by_css_selector('.flash').text,
                          "Returned %s" % (system.fqdn))

class SystemReturnTest(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.user = data_setup.create_user(password='password')
        self.system = data_setup.create_system(shared=True,
                status=SystemStatus.manual)
        self.lc  = data_setup.create_labcontroller(fqdn='remove_me')
        self.system.lab_controller = self.lc
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_cant_return_sneakily(self):
        self.login() #login as admin
        sel = self.selenium
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load(30000)
        sel.click('link=Take')
        sel.wait_for_page_to_load(30000)

        self.logout()
        self.login(user=self.user.user_name, password='password')
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load(30000)

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        sel.open('user_change?id=%s' % self.system.id)
        sel.wait_for_page_to_load("30000")
        self.assertIn('cannot unreserve system', sel.get_text('css=.flash'))

    def test_return_with_no_lc(self):
        sel = self.selenium
        self.login(user=self.user.user_name, password='password')
        sel.open('view/%s' % self.system.fqdn)
        sel.wait_for_page_to_load('30000')
        sel.click('link=Take')
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
        sel.click('link=Return')
        sel.wait_for_page_to_load('30000')
        text = sel.get_text('//body')
        self.assert_('Returned %s' % self.system.fqdn in text)


