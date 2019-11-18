# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import unittest as unittest
import requests
from selenium.webdriver.support.ui import Select
from bkr.server.model import SystemStatus, SSHPubKey, RenderedKickstart, \
    ConfigItem, User, Provision, SystemPermission
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, BootstrapSelect
from bkr.inttest.server.requests_utils import post_json
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base


class SystemProvisionWebUITest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.distro_tree = data_setup.create_distro_tree(
                osmajor=u'RedHatEnterpriseLinux6',
                lab_controllers=[self.lc])

    def go_to_provision_tab(self, system, refresh=True):
        b = self.browser
        if refresh:
            b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Provision').click()
        return b.find_element_by_id('provision')

    def go_to_essentials_tab(self, system, refresh=True):
        b = self.browser
        if refresh:
            b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Essentials').click()
        return b.find_element_by_id('essentials')

    def select_distro_tree(self, distro_tree):
        provision = self.browser.find_element_by_id('provision')
        Select(provision.find_element_by_name('osmajor')).select_by_visible_text(
            unicode(self.distro_tree.distro.osversion.osmajor))
        Select(provision.find_element_by_name('distro')).select_by_visible_text(
            unicode(self.distro_tree.distro))
        Select(provision.find_element_by_name('distro_tree_id')) \
            .select_by_visible_text(unicode(self.distro_tree))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1189432
    def test_distro_picker_widget_rerenders_upon_system_model_changes(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(arch=None)
            new_distro = data_setup.create_distro_tree(distro_name='AnweshasLinux',
                                                       osmajor='AnweshasLinux',
                                                       arch=u's390', lab_controllers=[lc])
        b = self.browser
        login(b)
        tab = self.go_to_essentials_tab(system=system)
        BootstrapSelect(tab.find_element_by_name('lab_controller_id')) \
            .select_by_visible_text(lc.fqdn.encode())
        BootstrapSelect(tab.find_element_by_name('arches')) \
            .select_by_visible_text('s390')
        tab.find_element_by_xpath('.//button[text()="Save Changes"]').click()
        b.find_element_by_xpath(
            '//div[@id="essentials"]//span[@class="sync-status" and not(text())]')
        tab = self.go_to_provision_tab(system=system, refresh=False)
        self.assertIn(u'AnweshasLinux',
                      [option.text for option in
                       Select(tab.find_element_by_name('osmajor')).options])

    def test_anonymous(self):
        with session.begin():
            system = data_setup.create_system()
        provision = self.go_to_provision_tab(system)
        provision.find_element_by_xpath('.//p[text()="You are not logged in."]')

    def test_no_lab_controller(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=None)
        login(self.browser)
        provision = self.go_to_provision_tab(system)
        provision.find_element_by_xpath('.//p[text()="System must be '
                                        'associated to a lab controller in order to provision."]')

    def test_no_arches(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lc)
            system.arch[:] = []
        login(self.browser)
        provision = self.go_to_provision_tab(system)
        provision.find_element_by_xpath('.//p[text()="System must have '
                                        'at least one supported architecture defined '
                                        'in order to provision."]')

    def test_no_permission(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(lab_controller=self.lc, shared=False)
        login(self.browser, user=user.user_name, password='testing')
        provision = self.go_to_provision_tab(system)
        provision.find_element_by_xpath('.//p[normalize-space(text())='
                                        '"You do not have access to provision this system."]')
        # 'control_system' permission does not grant permission to provision
        # https://bugzilla.redhat.com/show_bug.cgi?id=1144196
        with session.begin():
            system.custom_access_policy.add_rule(everybody=True,
                                                 permission=SystemPermission.control_system)
        provision = self.go_to_provision_tab(system)
        provision.find_element_by_xpath('.//p[normalize-space(text())='
                                        '"You do not have access to provision this system."]')

    def test_provision(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.manual,
                                              lab_controller=self.lc)
            system.reserve_manually(service=u'testdata', user=user)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        provision = self.go_to_provision_tab(system)
        self.select_distro_tree(self.distro_tree)
        provision.find_element_by_xpath('.//button[text()="Provision"]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                                '/h4[text()="Provisioning successful"]')
        with session.begin():
            self.assertEquals(system.installations[0].distro_tree, self.distro_tree)
            self.assertEquals(system.command_queue[0].action, 'on')
            self.assertEquals(system.command_queue[1].action, 'off')
            self.assertEquals(system.command_queue[2].action, 'configure_netboot')
            self.assertEquals(system.command_queue[3].action, 'clear_logs')

    def test_provision_with_ssh_key(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'AAAAvalidkeyyeah', u'user@host'))
            system = data_setup.create_system(status=SystemStatus.manual,
                                              lab_controller=self.lc)
            system.reserve_manually(service=u'testdata', user=user)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        provision = self.go_to_provision_tab(system)
        self.select_distro_tree(self.distro_tree)
        provision.find_element_by_xpath('.//button[text()="Provision"]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                                '/h4[text()="Provisioning successful"]')
        with session.begin():
            kickstart = RenderedKickstart.query.order_by(RenderedKickstart.id.desc()).first()
            self.assertIn('ssh-rsa AAAAvalidkeyyeah user@host', kickstart.kickstart)

    def test_provision_rejected_with_expired_root_password(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            user.root_password = "MothersMaidenName"
            user.rootpw_changed = datetime.datetime.utcnow() - datetime.timedelta(days=35)
            ConfigItem.by_name('root_password_validity').set(30,
                                                             user=User.by_user_name(
                                                                 data_setup.ADMIN_USER))
            system = data_setup.create_system(status=SystemStatus.manual,
                                              lab_controller=self.lc)
            system.reserve_manually(service=u'testdata', user=user)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        provision = self.go_to_provision_tab(system)
        self.select_distro_tree(self.distro_tree)
        provision.find_element_by_xpath('.//button[text()="Provision"]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        self.assertIn('root password has expired',
                      provision.find_element_by_class_name('alert-error').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=886875
    def test_kernel_option_with_multiple_values(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.manual,
                                              lab_controller=self.lc)
            system.provisions[self.distro_tree.arch] = \
                Provision(arch=self.distro_tree.arch,
                          kernel_options=u'key1=value1 key1=value2 key1 key2=value key3')
            system.reserve_manually(service=u'testdata', user=user)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        provision = self.go_to_provision_tab(system)
        self.select_distro_tree(self.distro_tree)
        provision.find_element_by_xpath('.//button[text()="Provision"]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                                '/h4[text()="Provisioning successful"]')
        self.assert_(u'key1=value1 key1=value2 key2=value key3' in \
                     system.installations[0].kernel_options)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1144195
    def test_refreshing_commands_grid_is_triggered_by_provision(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(owner=user, shared=True,
                                              lab_controller=self.lc)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        # load the commands grid first
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Power').click()
        # provision system
        b.find_element_by_link_text('Provision').click()
        provision = b.find_element_by_id('provision')
        self.select_distro_tree(self.distro_tree)
        provision.find_element_by_xpath('.//button[text()="Provision"]').click()
        b.find_element_by_xpath(
            './/div[contains(@class, "modal")]//button[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                                '/h4[text()="Provisioning successful"]')
        # check if the commands grid is refreshed
        b.find_element_by_link_text('Power').click()
        pane = b.find_element_by_id('power')
        pane.find_element_by_xpath('.//span[contains(text(), "Items found: %s")]'
                                   % len(system.command_queue))
        command_row = pane.find_element_by_xpath('.//table/tbody/tr[1]')
        command_row.find_element_by_xpath('./td[1]/a[text()="%s"]' % user.user_name)
        command_row.find_element_by_xpath('./td[6][text()="%s"]' % system.command_queue[0].action)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173446
    def test_link_to_reserve_workflow_appears_for_privileged_user(self):
        # Even if a user has permission to provision a system we want to offer
        # them a link to use the scheduler instead. Mainly this is because
        # a lot of people were caught out by the change in Beaker 19 to make
        # the provision tab always provision.
        with session.begin():
            owner = data_setup.create_user(password=u'owner')
            system = data_setup.create_system(owner=owner, lab_controller=self.lc)
        login(self.browser, user=owner.user_name, password=u'owner')
        provision = self.go_to_provision_tab(system)
        provision.find_element_by_xpath('.//a[text()="Reserve Workflow"]')


class SystemProvisionHTTPTest(unittest.TestCase):

    def setUp(self):
        self.system = data_setup.create_system(shared=True)
        self.system.custom_access_policy.add_rule(everybody=True,
                                                  permission=SystemPermission.control_system)

    def test_no_permission(self):
        with session.begin():
            user = data_setup.create_user(password='password')
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': user.user_name,
                                                  'password': 'password'}).raise_for_status()
        response = post_json(get_server_base() +
                             'systems/%s/installations/' % self.system.fqdn,
                             session=s, data={'distro_tree': {'id': -1}})
        self.assertEquals(response.status_code, 403)
        self.assertEquals(response.text,
                          'Insufficient permissions: Cannot provision system')
