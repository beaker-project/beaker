
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import (session, SystemStatus, SystemPermission,
                              Hypervisor, PowerType, ReleaseAction)
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class ModifySystemTest(ClientTestCase):

    def test_no_changes(self):
        try:
            run_client(['bkr', 'system-modify', 'fqdn.example'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('At least one option is required', e.stderr_output)

    def test_invalid_system(self):
        try:
            run_client(['bkr', 'system-modify', '--owner=somebody',
                        'ireallydontexistblah.test.fqdn'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('System not found', e.stderr_output)

    def test_change_owner(self):
        with session.begin():
            system1 = data_setup.create_system(shared=False)
            system2 = data_setup.create_system(shared=False)
            new_owner = data_setup.create_user()
        run_client(['bkr', 'system-modify', '--owner', new_owner.user_name,
                    system1.fqdn, system2.fqdn])
        with session.begin():
            session.expire_all()
            systems = [system1, system2]
            for system in systems:
                self.assertEquals(system.owner.user_name, new_owner.user_name)
                self.assertEquals(system.activity[-1].field_name, u'Owner')
                self.assertEquals(system.activity[-1].action, u'Changed')
                self.assertEquals(system.activity[-1].new_value,
                                  new_owner.user_name)

        # invalid user
        try:
            run_client(['bkr', 'system-modify', '--owner', 'idontexist',
                        system1.fqdn])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('No such user idontexist', e.stderr_output)

        # insufficient permission to change owner
        with session.begin():
            user1 = data_setup.create_user(password='abc')
        try:
            run_client(['bkr', 'system-modify', '--owner', user1.user_name,
                        '--password', 'abc',
                        '--user', user1.user_name,
                        system1.fqdn])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('Insufficient permissions: Cannot edit system',
                          e.stderr_output)

    def test_change_condition(self):
        with session.begin():
            system = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller(),
                status=SystemStatus.automated)
        run_client(['bkr', 'system-modify', '--condition=Manual', system.fqdn])
        with session.begin():
            session.expire_all()
            self.assertEquals(system.status, SystemStatus.manual)
            self.assertEquals(system.activity[0].field_name, u'Status')
            self.assertEquals(system.activity[0].new_value, u'Manual')

    def test_invalid_condition(self):
        with session.begin():
            system = data_setup.create_system()
        try:
            run_client(['bkr', 'system-modify',
                    '--condition=Unconditional', system.fqdn])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('option --condition: invalid choice', e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206978
    def test_change_hypervisor(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to KVM
        run_client(['bkr', 'system-modify', '--host-hypervisor=KVM', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.hypervisor, Hypervisor.by_name(u'KVM'))
        # set back to none (bare metal)
        run_client(['bkr', 'system-modify', '--host-hypervisor=', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.hypervisor, None)

    def test_modify_active_access_policy(self):
        with session.begin():
            user1 = data_setup.create_user()
            perm = SystemPermission.reserve
            system1 = data_setup.create_system(shared=False)
            system2 = data_setup.create_system(shared=False)
            system1.custom_access_policy.add_rule(perm, user=user1)
            system2.custom_access_policy.add_rule(perm, user=user1)

            pool = data_setup.create_system_pool(systems=[system1, system2])
            user2 = data_setup.create_user()
            pool.access_policy.add_rule(perm, user=user2)

        # use pool policy
        run_client(['bkr', 'system-modify',
                    '--pool-policy', pool.name,
                    system1.fqdn, system2.fqdn])
        with session.begin():
            session.expire_all()
            for s in [system1, system2]:
                self.assertFalse(s.active_access_policy.grants(user1, perm))
                self.assertTrue(s.active_access_policy.grants(user2, perm))
                self.assertEquals(s.activity[-1].field_name, u'Active Access Policy')
                self.assertEquals(s.activity[-1].action, u'Changed')
                self.assertEquals(s.activity[-1].old_value, 'Custom access policy' )
                self.assertEquals(s.activity[-1].new_value,'Pool policy: %s' % pool.name)

        # system not in a pool
        try:
            run_client(['bkr', 'system-modify',
                        '--pool-policy', data_setup.create_system_pool().name,
                        system1.fqdn])
        except ClientError as e:
            self.assertIn('To use a pool policy, the system must be in the pool first',
                          e.stderr_output)

        # Revert to custom policy
        run_client(['bkr', 'system-modify',
                    '--use-custom-policy',
                    system1.fqdn, system2.fqdn])

        with session.begin():
            session.expire_all()
            for s in [system1, system2]:
                self.assertTrue(s.active_access_policy.grants(user1, perm))
                self.assertFalse(s.active_access_policy.grants(user2, perm))

    def test_cannot_change_active_policy_without_permission(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system()
            system.custom_access_policy.add_rule(
                permission=SystemPermission.edit_system, user=user)
            pool = data_setup.create_system_pool(systems=[system])
        try:
            run_client(['bkr', 'system-modify',
                        '--pool-policy', pool.name,
                        '--user', user.user_name,
                        '--password', 'password',
                        system.fqdn])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('Cannot edit system access policy',
                          e.stderr_output)

    def test_modify_attributes_policy(self):
        with session.begin():
            system1 = data_setup.create_system(shared=False)
            system2 = data_setup.create_system(shared=False)
            new_owner = data_setup.create_user()
            perm = SystemPermission.reserve
            user1 = data_setup.create_user()
            system1.custom_access_policy.add_rule(perm, user=user1)
            system2.custom_access_policy.add_rule(perm, user=user1)
            pool = data_setup.create_system_pool(systems=[system1, system2])
            user2 = data_setup.create_user()
            pool.access_policy.add_rule(perm, user=user2)

        run_client(['bkr', 'system-modify',
                    '--owner', new_owner.user_name,
                    '--condition', 'Manual',
                    '--pool-policy', pool.name,
                    system1.fqdn, system2.fqdn])
        with session.begin():
            session.expire_all()
            for s in [system1, system2]:
                self.assertEquals(s.owner.user_name, new_owner.user_name)
                self.assertEquals(s.status, SystemStatus.manual)
                self.assertFalse(s.active_access_policy.grants(user1, perm))
                self.assertTrue(s.active_access_policy.grants(user2, perm))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1268811
    def test_no_fqdn(self):
        try:
            run_client(['bkr', 'system-modify'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('Specify one or more system FQDNs to modify', e.stderr_output)

    def test_change_power_type(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 'apc_snmp_then_etherwake'
        run_client(['bkr', 'system-modify',
                    '--power-type=apc_snmp_then_etherwake', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_type,
                              PowerType.by_name(u'apc_snmp_then_etherwake'))
        # set back to ilo
        run_client(['bkr', 'system-modify', '--power-type=ilo', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_type, PowerType.by_name(u'ilo'))

    def test_change_power_address(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 'dummyaddress'
        run_client(['bkr', 'system-modify', '--power-address=dummyaddress',
                    system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_address, u'dummyaddress')
        # set back to default value
        address = u'%s_power_address' % system.fqdn
        run_client(['bkr', 'system-modify', '--power-address=%s' % address,
                    system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_address, address)

    def test_change_power_user(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 'dummyuser'
        run_client(['bkr', 'system-modify', '--power-user=dummyuser', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_user, u'dummyuser')
        # set back to default value
        user = u'%s_power_user' % system.fqdn
        run_client(['bkr', 'system-modify', '--power-user=%s' % user, system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_user, user)

    def test_change_power_password(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 'dummypassword'
        run_client(['bkr', 'system-modify', '--power-password=dummypassword',
                    system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_passwd, u'dummypassword')
        # set back to default value
        password = u'%s_power_password' % system.fqdn
        run_client(['bkr', 'system-modify', '--power-password=%s' % password,
                    system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_passwd, password)

    def test_change_power_id(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 'dummyvm'
        run_client(['bkr', 'system-modify', '--power-id=dummyvm', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_id, u'dummyvm')
        # set to 'vm-dummy'
        run_client(['bkr', 'system-modify', '--power-id=vm-dummy', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_id, u'vm-dummy')

    def test_change_power_quiescent(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 10
        run_client(['bkr', 'system-modify', '--power-quiescent-period=10', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_quiescent_period, 10)
        # set to 5
        run_client(['bkr', 'system-modify', '--power-quiescent-period=5', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.power.power_quiescent_period, 5)

    def test_change_release_action(self):
        with session.begin():
            system = data_setup.create_system(hypervisor=None)
        # set to 'LeaveOn'
        run_client(['bkr', 'system-modify', '--release-action=LeaveOn', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.release_action, ReleaseAction.leave_on)
        # set to 'PowerOff'
        run_client(['bkr', 'system-modify', '--release-action=PowerOff', system.fqdn])
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.release_action, ReleaseAction.power_off)
