
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from bkr.server.model import session, System, Arch, KernelType, Hypervisor, \
    PowerType, ReleaseAction, SystemStatus, SystemType
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import post_json, login as requests_login

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
        requests_login(s, user=self.user, password=u'password')
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
            self.assertEqual(system.fqdn, fqdn)
            self.assertEqual(system.lab_controller_id, self.lc.id)
            self.assertTrue(Arch.by_name(u'i386') in system.arch)
            self.assertTrue(Arch.by_name(u'x86_64') in system.arch)
            self.assertEqual(system.location, u'dummylocation')
            self.assertEqual(system.lender, u'dummylender')
            self.assertEqual(system.kernel_type,  KernelType.by_name(u'highbank'))

    def test_creating_a_system_with_hardware_details(self):
        s = requests.Session()
        requests_login(s, user=self.user, password=u'password')
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
            self.assertEqual(system.fqdn, fqdn)
            self.assertEqual(system.hypervisor, Hypervisor.by_name(u'KVM'))
            self.assertEqual(system.location, u'dummylocation')
            self.assertEqual(system.serial, u'dummynumber')
            self.assertEqual(system.mac_address, u'dummymacaddress')
            self.assertEqual(system.memory, 111111)
            self.assertEqual(system.numa.nodes, 5)

    def test_creating_a_system_with_power_settings(self):
        s = requests.Session()
        requests_login(s, user=self.user, password=u'password')
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
            self.assertEqual(system.power.power_type, PowerType.by_name(u'apc_snmp_then_etherwake'))
            self.assertEqual(system.power.power_address, u'dummyaddress')
            self.assertEqual(system.power.power_user, u'dummyuser')
            self.assertEqual(system.power.power_passwd, u'dummypassword')
            self.assertEqual(system.power.power_id, u'dummyvm')
            self.assertEqual(system.power.power_quiescent_period, 5)
            self.assertEqual(system.release_action, ReleaseAction.leave_on)
            self.assertEqual(system.reprovision_distro_tree, self.distro_tree)

    def test_creating_a_system_with_scheduler_settings(self):
        s = requests.Session()
        requests_login(s, user=self.user, password=u'password')
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
            self.assertEqual(system.status, SystemStatus.broken)
            self.assertEqual(system.status_reason, u'Currently is broken')
            self.assertEqual(system.type, SystemType.laptop)
