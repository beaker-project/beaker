
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, System, SystemPermission, \
    User, Arch, PowerType, ReleaseAction
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class CreateSystem(ClientTestCase):

    def test_create_system_defaults(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        run_client(['bkr', 'system-create', fqdn])
        with session.begin():
            system = System.by_fqdn(fqdn, User.by_user_name(u'admin'))
            self.assertTrue(system.owner.user_name, data_setup.ADMIN_USER)
            self.assertTrue(system.custom_access_policy.grants_everybody(
                    SystemPermission.view))
        # duplicate
        try:
            run_client(['bkr', 'system-create', fqdn])
            self.fail('Must fail')
        except ClientError as e:
            self.assertIn("System with fqdn %r already exists" % fqdn,
                          e.stderr_output)

    def test_create_system_set_labcontroller(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        lc = data_setup.create_labcontroller()
        run_client(['bkr', 'system-create',
                    '--lab-controller', str(lc.fqdn),
                    fqdn])
        with session.begin():
            system = System.by_fqdn(fqdn, User.by_user_name(u'admin'))
            self.assertTrue(system.lab_controller, lc)

    def test_create_system_set_arches(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        run_client(['bkr', 'system-create',
                    '--arch', u'i386',
                    '--arch', u'x86_64',
                    fqdn])
        with session.begin():
            system = System.by_fqdn(fqdn, User.by_user_name(u'admin'))
            self.assertIn(Arch.by_name(u'i386'), system.arch)
            self.assertIn(Arch.by_name(u'x86_64'), system.arch)

    def test_create_system_set_power_settings(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        distro_tree = data_setup.create_distro_tree()
        run_client(['bkr', 'system-create',
                    '--power-type', u'apc_snmp_then_etherwake',
                    '--power-address', u'dummyaddress',
                    '--power-user', u'dummyuser',
                    '--power-password', u'dummypassword',
                    '--power-id', u'dummyvm',
                    '--power-quiescent-period', u'5',
                    '--release-action', u'LeaveOn',
                    '--reprovision-distro-tree', str(distro_tree.id),
                    fqdn])
        with session.begin():
            system = System.by_fqdn(fqdn, User.by_user_name(u'admin'))
            self.assertEquals(system.power.power_type, PowerType.by_name(u'apc_snmp_then_etherwake'))
            self.assertEquals(system.power.power_address, u'dummyaddress')
            self.assertEquals(system.power.power_user, u'dummyuser')
            self.assertEquals(system.power.power_passwd, u'dummypassword')
            self.assertEquals(system.power.power_id, u'dummyvm')
            self.assertEquals(system.power.power_quiescent_period, 5)
            self.assertEquals(system.release_action, ReleaseAction.leave_on)
            self.assertEquals(system.reprovision_distro_tree, distro_tree)

    def test_create_system_set_host_hypervisor(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        run_client(['bkr', 'system-create', fqdn,
                    '--host-hypervisor=KVM'])
        with session.begin():
            system = System.by_fqdn(fqdn, User.by_user_name(u'admin'))
            self.assertEquals(str(system.hypervisor), u'KVM')
            self.assertEquals(system.activity[0].new_value, u'KVM')

    def test_create_system_set_condition(self):
        fqdn = data_setup.unique_name(u'mysystem%s')
        with session.begin():
            lc = data_setup.create_labcontroller()
        run_client(['bkr', 'system-create', fqdn,
                    '--lab-controller', str(lc.fqdn),
                    '--condition=Automated'])
        with session.begin():
            system = System.by_fqdn(fqdn, User.by_user_name(u'admin'))
            self.assertTrue(system.lab_controller, lc)
            self.assertEquals(str(system.status), u'Automated')
