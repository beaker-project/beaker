
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from bkr.server.model import session, SystemPermission, SystemStatus, \
        Command, CommandStatus
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.requests_utils import login as requests_login, post_json
from bkr.inttest.server.webdriver_utils import login

class SystemCommandsTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password=u'owner')
            self.privileged = data_setup.create_user(password=u'privileged')
            self.system = data_setup.create_system(owner=self.owner, shared=True,
                    lab_controller=data_setup.create_labcontroller())
            data_setup.configure_system_power(self.system)
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.control_system,
                    user=self.privileged)
            self.unprivileged = data_setup.create_user(password=u'unprivileged')
            data_setup.create_running_job(system=self.system)
        self.browser = self.get_browser()

    def go_to_commands_tab(self, system):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Power').click()

    def check_cannot_power(self, user, password, system, error_message):
        b = self.browser
        login(b, user.user_name, password)
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//div[contains(@class, "alert") and text()="%s."]'
                % error_message)
        # try issuing the request directly also
        s = requests.Session()
        requests_login(s, user.user_name, password)
        response = post_json(get_server_base() +
                'systems/%s/commands/' % system.fqdn,
                session=s, data=dict(action='on'))
        self.assertGreaterEqual(response.status_code, 400)
        self.assertIn(error_message, response.text)

    def check_cannot_clear_netboot(self, user, password, system, error_message):
        b = self.browser
        login(b, user.user_name, password)
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//div[contains(@class, "alert") and text()="%s."]'
                % error_message)
        # try issuing the request directly also
        s = requests.Session()
        requests_login(s, user.user_name, password)
        response = post_json(get_server_base() +
                'systems/%s/commands/' % system.fqdn,
                session=s, data=dict(action='clear_netboot'))
        self.assertGreaterEqual(response.status_code, 400)
        self.assertIn(error_message, response.text)

    def check_power_on(self, system):
        b = self.browser
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//button[normalize-space(string(.))="Power On"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
                'power the system on?"]')
        modal.find_element_by_xpath('.//strong[text()='
                '"You are not the current user of the system. '
                'This action may interfere with another user."]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        pane.find_element_by_xpath('.//table/tbody/tr[1]/td[6][text()="on"]')
        with session.begin():
            session.expire_all()
            self.assertEquals(system.command_queue[0].action, 'on')

    def check_clear_netboot(self, system):
        b = self.browser
        self.go_to_commands_tab(system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//button[normalize-space(string(.))="Clear Netboot"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to '
                'clear the system\'s netboot configuration?"]')
        modal.find_element_by_xpath('.//strong[text()='
                '"You are not the current user of the system. '
                'This action may interfere with another user."]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        pane.find_element_by_xpath('.//table/tbody/tr[1]/td[6][text()="clear_netboot"]')
        with session.begin():
            session.expire_all()
            self.assertEquals(system.command_queue[0].action, 'clear_netboot')

    def test_cannot_power_when_not_logged_in(self):
        b = self.browser
        self.go_to_commands_tab(self.system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//div[contains(@class, "alert") and '
                'text()="You are not logged in."]')
        # try issuing the request directly also
        response = post_json(get_server_base() +
                'systems/%s/commands/' % self.system.fqdn,
                data=dict(action='on'))
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.text, 'Authenticated user required')

    def test_cannot_power_without_permission(self):
        self.check_cannot_power(self.unprivileged, 'unprivileged',
                self.system, 'You do not have permission to control this system')

    # https://bugzilla.redhat.com/show_bug.cgi?id=740321
    def test_cannot_power_system_without_lc(self):
        with session.begin():
            system = data_setup.create_system(owner=self.owner)
            self.assertEqual(system.status, SystemStatus.manual)
        self.check_cannot_power(self.owner, 'owner', system,
                'System is not attached to a lab controller')

    def test_power_on(self):
        login(self.browser, user=self.owner.user_name, password='owner')
        self.check_power_on(self.system)

    def test_can_power_with_permission(self):
        login(self.browser, user=self.privileged.user_name, password='privileged')
        self.check_power_on(self.system)

    def test_cannot_clear_netboot_without_permission(self):
        self.check_cannot_clear_netboot(self.unprivileged, 'unprivileged',
                self.system, 'You do not have permission to control this system')

    def test_clear_netboot(self):
        login(self.browser, user=self.owner.user_name, password='owner')
        self.check_clear_netboot(self.system)

    def test_can_clear_netboot_with_permission(self):
        login(self.browser, user=self.privileged.user_name, password='privileged')
        self.check_clear_netboot(self.system)

    def test_can_filter_commands_by_start_time(self):
        with session.begin():
            self.system.command_queue.extend([
                Command(action=u'interrupt', service=u'testdata',
                    status=CommandStatus.queued),
                Command(action=u'off', service=u'testdata',
                    status=CommandStatus.completed,
                    start_time=datetime.datetime(2016, 9, 7, 0, 0, 1),
                    finish_time=datetime.datetime(2016, 9, 7, 0, 0, 2)),
                Command(action=u'on', service=u'testdata',
                    status=CommandStatus.completed,
                    start_time=datetime.datetime(2016, 9, 6, 0, 0, 1),
                    finish_time=datetime.datetime(2016, 9, 6, 0, 0, 2)),
            ])
        b = self.browser
        self.go_to_commands_tab(self.system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//input[@type="search"]')\
            .send_keys('start_time:2016-09-06')
        pane.find_element_by_xpath('.//table['
                'not(tbody/tr/td[6]/text()="interrupt") and '
                'not(tbody/tr/td[6]/text()="off") and '
                'tbody/tr/td[6]/text()="on"]')

    def test_can_filter_commands_by_finish_time(self):
        with session.begin():
            self.system.command_queue.extend([
                Command(action=u'interrupt', service=u'testdata',
                    status=CommandStatus.running,
                    start_time=datetime.datetime(2015, 12, 7, 0, 0, 0)),
                Command(action=u'off', service=u'testdata',
                    status=CommandStatus.completed,
                    start_time=datetime.datetime(2015, 12, 6, 0, 0, 2),
                    finish_time=datetime.datetime(2015, 12, 7, 0, 0, 0)),
                Command(action=u'on', service=u'testdata',
                    status=CommandStatus.completed,
                    start_time=datetime.datetime(2015, 12, 6, 0, 0, 1),
                    finish_time=datetime.datetime(2015, 12, 6, 0, 0, 2)),
            ])
        b = self.browser
        self.go_to_commands_tab(self.system)
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//input[@type="search"]')\
            .send_keys('finish_time:2015-12-06')
        pane.find_element_by_xpath('.//table['
                'not(tbody/tr/td[6]/text()="interrupt") and '
                'not(tbody/tr/td[6]/text()="off") and '
                'tbody/tr/td[6]/text()="on"]')
