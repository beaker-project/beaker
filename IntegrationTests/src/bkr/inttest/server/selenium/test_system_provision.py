
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from selenium.webdriver.support.ui import Select
from bkr.server.model import SystemStatus, SSHPubKey, RenderedKickstart, \
        ConfigItem, User, Provision
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base

class SystemProvisionTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.distro_tree = data_setup.create_distro_tree(
                    osmajor=u'RedHatEnterpriseLinux6',
                    lab_controllers=[self.lc])

    def go_to_provision_tab(self, system):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Provision').click()
        return b.find_element_by_id('provision')

    def select_distro_tree(self, distro_tree):
        provision = self.browser.find_element_by_id('provision')
        Select(provision.find_element_by_name('osmajor')).select_by_visible_text(
            unicode(self.distro_tree.distro.osversion.osmajor))
        Select(provision.find_element_by_name('distro')).select_by_visible_text(
            unicode(self.distro_tree.distro))
        Select(provision.find_element_by_name('distro_tree_id'))\
            .select_by_visible_text(unicode(self.distro_tree))

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
                '"You do not have access to control this system."]')

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
                './/div[contains(@class, "modal")]//a[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Provisioning successful"]')
        with session.begin():
            self.assertEquals(system.command_queue[0].action, 'on')
            self.assertEquals(system.command_queue[1].action, 'off')
            self.assertEquals(system.command_queue[2].action, 'configure_netboot')
            self.assertEquals(system.command_queue[2].distro_tree, self.distro_tree)
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
                './/div[contains(@class, "modal")]//a[text()="OK"]').click()
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
                    user=User.by_user_name(data_setup.ADMIN_USER))
            system = data_setup.create_system(status=SystemStatus.manual,
                    lab_controller=self.lc)
            system.reserve_manually(service=u'testdata', user=user)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        provision = self.go_to_provision_tab(system)
        self.select_distro_tree(self.distro_tree)
        provision.find_element_by_xpath('.//button[text()="Provision"]').click()
        b.find_element_by_xpath(
                './/div[contains(@class, "modal")]//a[text()="OK"]').click()
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
                './/div[contains(@class, "modal")]//a[text()="OK"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Provisioning successful"]')
        self.assertEquals(system.command_queue[2].action, 'configure_netboot')
        self.assert_(u'key1=value1 key1=value2 key2=value key3' in \
                         system.command_queue[2].kernel_options)
