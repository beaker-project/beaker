
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from selenium.webdriver.support.ui import Select
from bkr.server.model import session, System, SystemPermission, Arch, \
    KernelType, Hypervisor, PowerType, ReleaseAction, SystemStatus, \
    SystemType
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import post_json

class AddSystem(WebDriverTestCase):
    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser)

    def test_add_system(self):
        fqdn = u'test-system-1'
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys(fqdn)
        b.find_element_by_xpath('//button[text()="Add"]').click()
        # should go to system page
        b.find_element_by_xpath('//h1[text()="%s"]' % fqdn)

    def test_cannot_add_existing_system(self):
        with session.begin():
            data_setup.create_system(fqdn=u'preexisting-system')
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys('preexisting-system')
        b.find_element_by_xpath('//button[text()="Add"]').click()
        # this is not ideal...
        b.find_element_by_xpath('''//*[text()="System with fqdn u'preexisting-system' already exists"]''')

    #https://bugzilla.redhat.com/show_bug.cgi?id=1021737
    def test_empty_fqdn(self):

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        # leave the fqdn field blank
        b.find_element_by_xpath('//button[text()="Add"]').click()
        # we can't actually check the HTML5 validation error,
        # but we should still be at the system modal
        b.find_element_by_css_selector('input[name=fqdn]:required')

    def test_grants_view_permission_to_everybody_by_default(self):
        fqdn = data_setup.unique_name(u'test-add-system%s.example.invalid')
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys(fqdn)
        b.find_element_by_xpath('//button[text()="Add"]').click()
        b.find_element_by_xpath('//h1[text()="%s"]' % fqdn)
        with session.begin():
            system = System.query.filter(System.fqdn == fqdn).one()
            self.assertTrue(system.custom_access_policy.grants_everybody(
                    SystemPermission.view))


# https://bugzilla.redhat.com/show_bug.cgi?id=1323885
class CreateSystemHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by bkr system-create.
    """
    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
            self.lc = data_setup.create_labcontroller()
            self.distro_tree = data_setup.create_distro_tree()

    def test_creating_a_system_with_hardware_essentials(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.user.user_name,
                                                  'password': u'password'}).raise_for_status()
        fqdn = data_setup.unique_name(u'newsystem%s')
        data = {
            'fqdn': fqdn,
            'lab_controller_id': self.lc.id,
            'arches': [u'i386', u'x86_64'],
            'location': u'dummylocation',
            'lender': u'dummylender',
            'kernel_type': u'highbank'
        }
        response = post_json(get_server_base() + 'systems/', session=s, data=data)
        with session.begin():
            system = System.by_fqdn(fqdn, self.user)
            self.assertEquals(system.fqdn, fqdn)
            self.assertEquals(system.lab_controller_id, self.lc.id)
            self.assertTrue(Arch.by_name(u'i386') in system.arch)
            self.assertTrue(Arch.by_name(u'x86_64') in system.arch)
            self.assertEquals(system.location, u'dummylocation')
            self.assertEquals(system.lender, u'dummylender')
            self.assertEquals(system.kernel_type,  KernelType.by_name(u'highbank'))

    def test_creating_a_system_with_hardware_details(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.user.user_name,
                                                  'password': u'password'}).raise_for_status()
        fqdn = data_setup.unique_name(u'newsystem%s')
        data = {
            'fqdn': fqdn,
            'hypervisor': u'KVM',
            'vendor': u'dummyvendor',
            'location': u'dummylocation',
            'model': u'dummymodel',
            'serial_number': u'dummynumber',
            'mac_address': u'dummymacaddress',
            'memory': 111111,
            'numa_nodes': 5,
        }
        response = post_json(get_server_base() + 'systems/', session=s, data=data)
        with session.begin():
            system = System.by_fqdn(fqdn, self.user)
            self.assertEquals(system.fqdn, fqdn)
            self.assertEquals(system.hypervisor, Hypervisor.by_name(u'KVM'))
            self.assertEquals(system.location, u'dummylocation')
            self.assertEquals(system.serial, u'dummynumber')
            self.assertEquals(system.mac_address, u'dummymacaddress')
            self.assertEquals(system.memory, 111111)
            self.assertEquals(system.numa.nodes, 5)

    def test_creating_a_system_with_power_settings(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.user.user_name,
                                                  'password': u'password'}).raise_for_status()
        fqdn = data_setup.unique_name(u'newsystem%s')
        data = {
            'fqdn': fqdn,
            'lab_controller_id': self.lc.id,
            'power_type': u'apc_snmp_then_etherwake',
            'power_address': u'dummyaddress',
            'power_user': u'dummyuser',
            'power_password': u'dummypassword',
            'power_id': u'dummyvm',
            'power_quiescent_period': 5,
            'release_action': u'LeaveOn',
            'reprovision_distro_tree': {'id': self.distro_tree.id},
        }
        response = post_json(get_server_base() + 'systems/', session=s, data=data)
        with session.begin():
            system = System.by_fqdn(fqdn, self.user)
            self.assertEquals(system.power.power_type, PowerType.by_name(u'apc_snmp_then_etherwake'))
            self.assertEquals(system.power.power_address, u'dummyaddress')
            self.assertEquals(system.power.power_user, u'dummyuser')
            self.assertEquals(system.power.power_passwd, u'dummypassword')
            self.assertEquals(system.power.power_id, u'dummyvm')
            self.assertEquals(system.power.power_quiescent_period, 5)
            self.assertEquals(system.release_action, ReleaseAction.leave_on)
            self.assertEquals(system.reprovision_distro_tree, self.distro_tree)

    def test_creating_a_system_with_scheduler_settings(self):
        s = requests.Session()
        s.post(get_server_base() + 'login', data={'user_name': self.user.user_name,
                                                  'password': u'password'}).raise_for_status()
        fqdn = data_setup.unique_name(u'newsystem%s')
        data = {
            'fqdn': fqdn,
            'status': u'Broken',
            'status_reason': u'Currently is broken',
            'type': u'Laptop',
        }
        response = post_json(get_server_base() + 'systems/', session=s, data=data)
        with session.begin():
            system = System.by_fqdn(fqdn, self.user)
            self.assertEquals(system.status, SystemStatus.broken)
            self.assertEquals(system.status_reason, u'Currently is broken')
            self.assertEquals(system.type, SystemType.laptop)
