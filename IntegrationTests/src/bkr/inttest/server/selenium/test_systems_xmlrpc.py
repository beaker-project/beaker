
# vim: set fileencoding=utf-8:

# Beaker
#
# Copyright (C) 2010 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import unittest
import logging
import time
import datetime
import xmlrpclib
import crypt
from turbogears.database import session

from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest.assertions import assert_datetime_within, \
        assert_durations_not_overlapping
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import User, Cpu, Key, Key_Value_String, Key_Value_Int, \
        System, SystemActivity, Provision, Hypervisor, SSHPubKey, ConfigItem, \
        RenderedKickstart, SystemStatus, ReleaseAction

class ReserveSystemXmlRpcTest(XmlRpcTestCase):

    def test_cannot_reserve_when_not_logged_in(self):
        with session.begin():
            system = data_setup.create_system()
        server = self.get_server()
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_('Anonymous access denied' in e.faultString, e.faultString)

    def test_cannot_reserve_automated_system(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assertIn('Cannot manually reserve automated system', e.faultString)

    def test_cannot_reserve_system_in_use(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system(owner=user, status=u'Manual', shared=True)
            system.user = User.by_user_name(data_setup.ADMIN_USER)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assertIn('already reserved', e.faultString)

    def test_reserve_system(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            self.assert_(system.user is None)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
        with session.begin():
            session.refresh(system)
            self.assertEqual(system.user, user)
            self.assertEqual(system.reservations[0].type, u'manual')
            self.assertEqual(system.reservations[0].user, user)
            self.assert_(system.reservations[0].finish_time is None)
            assert_durations_not_overlapping(system.reservations)
            reserved_activity = system.activity[-1]
            self.assertEqual(reserved_activity.action, 'Reserved')
            self.assertEqual(reserved_activity.field_name, 'User')
            self.assertEqual(reserved_activity.user, user)
            self.assertEqual(reserved_activity.new_value, user.user_name)
            self.assertEqual(reserved_activity.service, 'XMLRPC')

    def test_double_reserve(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            self.assert_(system.user is None)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('has already reserved system' in e.faultString)

    def test_reserve_via_external_service(self):
        with session.begin():
            service_group = data_setup.create_group(permissions=[u'proxy_auth'])
            service_user = data_setup.create_user(password=u'password')
            data_setup.add_user_to_group(service_user, service_group)
            user = data_setup.create_user(password=u'notused')
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            self.assert_(system.user is None)
        server = self.get_server()
        server.auth.login_password(service_user.user_name, 'password',
                user.user_name)
        server.systems.reserve(system.fqdn)
        with session.begin():
            session.refresh(system)
            self.assertEqual(system.user, user)
            self.assertEqual(system.reservations[0].type, u'manual')
            self.assertEqual(system.reservations[0].user, user)
            self.assert_(system.reservations[0].finish_time is None)
            assert_durations_not_overlapping(system.reservations)
            reserved_activity = system.activity[0]
            self.assertEqual(reserved_activity.action, 'Reserved')
            self.assertEqual(reserved_activity.service, service_user.user_name)

class ReleaseSystemXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.lab_controller = data_setup.create_labcontroller()

    def test_cannot_release_when_not_logged_in(self):
        with session.begin():
            system = data_setup.create_system()
        server = self.get_server()
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_('Anonymous access denied' in e.faultString, e.faultString)

    def test_cannot_release_when_not_current_user(self):
        with session.begin():
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            user = data_setup.create_user(password=u'password')
            other_user = data_setup.create_user()
            system.reserve(service=u'testdata', user=other_user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assertIn('cannot unreserve system', e.faultString)

    def test_release_system(self):
        with session.begin():
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            user = data_setup.create_user(password=u'password')
            system.reserve(service=u'testdata', user=user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        with session.begin():
            session.refresh(system)
            session.refresh(system.reservations[0])
            self.assert_(system.user is None)
            self.assertEquals(system.reservations[0].user, user)
            assert_datetime_within(system.reservations[0].finish_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow())
            assert_durations_not_overlapping(system.reservations)
            released_activity = system.activity[0]
            self.assertEqual(released_activity.action, 'Returned')
            self.assertEqual(released_activity.field_name, 'User')
            self.assertEqual(released_activity.user, user)
            self.assertEqual(released_activity.old_value, user.user_name)
            self.assertEqual(released_activity.new_value, '')
            self.assertEqual(released_activity.service, 'XMLRPC')

    def test_double_release(self):
        with session.begin():
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            user = data_setup.create_user(password=u'password')
            system.reserve(service=u'testdata', user=user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System %s is not currently reserved' % system.fqdn in e.faultString)

    # https://bugzilla.redhat.com/show_bug.cgi?id=820779
    def test_release_action_leaveon(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lab_controller)
            system.release_action = ReleaseAction.leave_on
            user = data_setup.create_user(password=u'password')
            system.reserve(service=u'testdata', user=user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        with session.begin():
            session.expire(system)
            self.assertEquals(system.command_queue[0].action, 'on')
            self.assertEquals(system.command_queue[1].action, 'clear_netboot')

    # https://bugzilla.redhat.com/show_bug.cgi?id=820779
    def test_release_action_reprovision(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lab_controller)
            system.release_action = ReleaseAction.reprovision
            system.reprovision_distro_tree = data_setup.create_distro_tree(
                    osmajor=u'Fedora')
            user = data_setup.create_user(password=u'password')
            system.reserve(service=u'testdata', user=user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        with session.begin():
            session.expire(system)
            self.assertEquals(system.command_queue[0].action, 'reboot')
            self.assertEquals(system.command_queue[1].action, 'configure_netboot')
            self.assertEquals(system.command_queue[2].action, 'clear_logs')
            self.assertEquals(system.command_queue[3].action, 'clear_netboot')

    # https://bugzilla.redhat.com/show_bug.cgi?id=837710
    def test_reprovision_failure(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lab_controller)
            system.release_action = ReleaseAction.reprovision
            system.reprovision_distro_tree = data_setup.create_distro_tree(
                    osmajor=u'BrokenDistro')
            user = data_setup.create_user(password=u'password')
            system.reserve(service=u'testdata', user=user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        with session.begin():
            session.expire(system)
            self.assertEquals(system.command_queue[0].action, 'clear_netboot')
            self.assert_(system.user is None, system.user)

    # https://bugzilla.redhat.com/show_bug.cgi?id=824257
    def test_release_action_unset(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lab_controller)
            system.release_action = None
            user = data_setup.create_user(password=u'password')
            system.reserve(service=u'testdata', user=user)
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        with session.begin():
            session.expire(system)
            self.assertEquals(system.command_queue[0].action, 'off')
            self.assertEquals(system.command_queue[1].action, 'clear_netboot')

class SystemPowerXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.lab_controller = data_setup.create_labcontroller()
        self.server = self.get_server()

    def test_cannot_power_when_not_logged_in(self):
        try:
            self.server.systems.power('on', 'fqdn')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('Anonymous access denied' in e.faultString, e.faultString)

    def test_cannot_power_system_in_use(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            other_user = data_setup.create_user()
            system = data_setup.create_system()
            system.user = other_user
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.power('on', system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is in use' in e.faultString)
        with session.begin():
            self.assertEquals(system.command_queue, [])

    def check_power_action(self, action):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system()
            data_setup.configure_system_power(system)
            system.lab_controller = self.lab_controller
            system.user = None
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power(action, system.fqdn)
        self.assertEqual(
                System.by_fqdn(system.fqdn, user).command_queue[0].action,
                action)

    def test_power_on(self):
        self.check_power_action('on')

    def test_power_off(self):
        self.check_power_action('off')

    def test_reboot(self):
        self.check_power_action('reboot')

    def test_can_force_powering_system_in_use(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            other_user = data_setup.create_user()
            system = data_setup.create_system()
            data_setup.configure_system_power(system)
            system.lab_controller = self.lab_controller
            system.user = other_user
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power('on', system.fqdn, False, True)
        with session.begin():
            self.assertEqual(system.command_queue[0].action, 'on')

    def test_clear_netboot(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            system = data_setup.create_system()
            data_setup.configure_system_power(system)
            system.lab_controller = self.lab_controller
            system.user = None
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power('reboot', system.fqdn, True)
        with session.begin():
            self.assertEqual(system.command_queue[0].action, 'reboot')
            self.assertEqual(system.command_queue[1].action, 'clear_netboot')

class SystemProvisionXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.lab_controller = data_setup.create_labcontroller()
        self.distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora',
                arch=u'i386', lab_controllers=[self.lab_controller])
        self.usable_system = data_setup.create_system(arch=u'i386',
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        data_setup.configure_system_power(self.usable_system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        self.usable_system.lab_controller = self.lab_controller
        self.usable_system.user = data_setup.create_user(password=u'password')
        self.usable_system.provisions[self.distro_tree.arch] = Provision(
                arch=self.distro_tree.arch,
                kernel_options='ksdevice=eth0 console=ttyS0')
        self.server = self.get_server()

    def test_cannot_provision_when_not_logged_in(self):
        try:
            self.server.systems.provision('fqdn', 'distro')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('Anonymous access denied' in e.faultString, e.faultString)

    def test_cannot_provision_automated_system(self):
        with session.begin():
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Automated', shared=True)
            user = data_setup.create_user(password=u'password')
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, 'distro')
        except xmlrpclib.Fault, e:
            self.assertIn('Reserve a system before provisioning', e.faultString)
        with session.begin():
            self.assertEquals(system.command_queue, [])

    def test_cannot_provision_system_in_use(self):
        with session.begin():
            system = data_setup.create_system(
                    owner=User.by_user_name(data_setup.ADMIN_USER),
                    status=u'Manual', shared=True)
            user = data_setup.create_user(password=u'password')
            other_user = data_setup.create_user()
            system.user = other_user
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, 'distro')
        except xmlrpclib.Fault, e:
            self.assert_('Reserve a system before provisioning'
                    in e.faultString)
        with session.begin():
            self.assertEquals(system.command_queue, [])

    def test_provision(self):
        kickstart = '''
            %pre
            kickstart lol!
            do some stuff etc
            '''
        system = self.usable_system
        self.server.auth.login_password(system.user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro_tree.id,
                'method=nfs',
                'noapic',
                'noapic runlevel=3',
                kickstart)
        with session.begin():
            rendered_kickstart = RenderedKickstart.query\
                    .order_by(RenderedKickstart.id.desc()).first()
            self.assert_(kickstart in rendered_kickstart.kickstart)
            self.assertEquals(system.command_queue[0].action, 'reboot')
            self.assertEquals(system.command_queue[1].action, 'configure_netboot')
            self.assertEquals(system.command_queue[1].distro_tree, self.distro_tree)
            self.assertEquals(system.command_queue[1].kernel_options,
                    'console=ttyS0 ks=%s ksdevice=eth0 noapic noverifyssl' % rendered_kickstart.link)
            self.assertEquals(system.command_queue[2].action, 'clear_logs')

    def test_provision_without_reboot(self):
        system = self.usable_system
        self.server.auth.login_password(system.user.user_name,
                'password')
        self.server.systems.provision(system.fqdn,
                self.distro_tree.id, None, None, None, None,
                False) # this last one is reboot=False
        with session.begin():
            self.assertEquals(system.command_queue[0].action, 'configure_netboot')
            self.assertEquals(system.command_queue[1].action, 'clear_logs')
            self.assertEquals(len(system.command_queue), 2, system.command_queue)

    def test_refuses_to_provision_distro_with_mismatched_arch(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64')
        self.server.auth.login_password(self.usable_system.user.user_name,
                'password')
        try:
            self.server.systems.provision(self.usable_system.fqdn, distro_tree.id)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('cannot be provisioned on system' in e.faultString)
        with session.begin():
            self.assertEquals(self.usable_system.command_queue, [])

    def test_refuses_to_provision_distro_not_in_lc(self):
        with session.begin():
            self.distro_tree.lab_controller_assocs[:] = []
        self.server.auth.login_password(self.usable_system.user.user_name,
                'password')
        try:
            self.server.systems.provision(self.usable_system.fqdn, self.distro_tree.id)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('cannot be provisioned on system' in e.faultString)
        with session.begin():
            self.assertEquals(self.usable_system.command_queue, [])

    def test_kernel_options_inherited_from_defaults(self):
        system = self.usable_system
        self.server.auth.login_password(system.user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro_tree.id,
                None, 'ksdevice=eth1')
        with session.begin():
            # console=ttyS0 comes from arch default, created in setUp()
            self.assertEquals(system.command_queue[0].action, 'reboot')
            self.assert_('console=ttyS0' in system.command_queue[1].kernel_options)
            self.assert_('ksdevice=eth1' in system.command_queue[1].kernel_options)
            self.assert_('ksdevice=eth0' not in system.command_queue[1].kernel_options)

    def test_provision_expired_user_root_password(self):
        system = self.usable_system
        user = system.user
        with session.begin():
            user.root_password = 'gyfrinachol'
            user.rootpw_changed = datetime.datetime.utcnow() - datetime.timedelta(days=99)
            ConfigItem.by_name('root_password_validity')\
                      .set(90, user=User.by_user_name(data_setup.ADMIN_USER))
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, self.distro_tree.id)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('root password has expired' in e.faultString, e.faultString)
        with session.begin():
            self.assertEquals(system.command_queue, [])


class LegacyPushXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=658503
    def test_system_activity_shows_changes(self):
        with session.begin():
            system = data_setup.create_system()
            system.key_values_string.extend([
                Key_Value_String(Key.by_name(u'PCIID'), '1022:2000'),
                Key_Value_String(Key.by_name(u'PCIID'), '80ee:beef'),
            ])
        self.server.legacypush(system.fqdn,
                {'PCIID': ['80ee:cafe', '80ee:beef']})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].field_name, u'Key/Value')
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Added')
            self.assertEquals(system.activity[0].old_value, None)
            self.assertEquals(system.activity[0].new_value, u'PCIID/80ee:cafe')
            self.assertEquals(system.activity[1].field_name, u'Key/Value')
            self.assertEquals(system.activity[1].service, u'XMLRPC')
            self.assertEquals(system.activity[1].action, u'Removed')
            self.assertEquals(system.activity[1].old_value, u'PCIID/1022:2000')
            self.assertEquals(system.activity[1].new_value, None)

    def test_bools_are_coerced_to_ints(self):
        with session.begin():
            system = data_setup.create_system()
            system.key_values_string.append(
                    Key_Value_String(Key.by_name(u'HVM'), '0'))

        self.server.legacypush(system.fqdn, {'HVM': False})
        with session.begin():
            session.refresh(system)
            self.assertEquals(len(system.activity), 0) # nothing has changed, yet

        self.server.legacypush(system.fqdn, {'HVM': True})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].field_name, u'Key/Value')
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Added')
            self.assertEquals(system.activity[0].old_value, None)
            self.assertEquals(system.activity[0].new_value, u'HVM/1')

    # https://bugzilla.redhat.com/show_bug.cgi?id=665441
    def test_existing_keys_are_untouched(self):
        with session.begin():
            system = data_setup.create_system()
            system.key_values_string.extend([
                Key_Value_String(Key.by_name(u'PCIID'), '1022:2000'), # this one gets deleted
                Key_Value_String(Key.by_name(u'HVM'), '0'), # this one gets updated
                Key_Value_String(Key.by_name(u'VENDOR'), 'Bob'), # this one should not be touched
            ])

        self.server.legacypush(system.fqdn, {'PCIID': [], 'HVM': True})
        with session.begin():
            session.refresh(system)
            self.assertEquals(len(system.key_values_string), 2, system.key_values_string)
            self.assertEquals(system.key_values_string[0].key.key_name, u'VENDOR')
            self.assertEquals(system.key_values_string[0].key_value, u'Bob')
            self.assertEquals(system.key_values_string[1].key.key_name, u'HVM')
            self.assertEquals(system.key_values_string[1].key_value, u'1')

class PushXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=658503

    def test_system_activity_shows_changes_for_simple_attributes(self):
        with session.begin():
            system = data_setup.create_system()
            system.vendor = None
            system.model = None
            system.memory = None
        self.server.push(system.fqdn,
                {'vendor': 'Acorn', 'model': 'Archimedes', 'memory': '16'})
        with session.begin():
            session.refresh(system)
            # no way to know in which order the changes will be recorded :-(
            changes = system.activity[:4]
            for change in changes:
                self.assertEquals(change.service, u'XMLRPC')
                self.assertEquals(change.action, u'Changed')
            changed_fields = set(change.field_name for change in changes)
            self.assertEquals(changed_fields,
                    set(['checksum', 'vendor', 'model', 'memory']))

    def test_system_activity_shows_changes_for_arches(self):
        with session.begin():
            system = data_setup.create_system()
        self.server.push(system.fqdn, {'Arch': ['sparc32']})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Added')
            self.assertEquals(system.activity[0].field_name, u'Arch')
            self.assertEquals(system.activity[0].old_value, None)
            self.assertEquals(system.activity[0].new_value, u'sparc32')
            self.assertEquals(system.activity[1].service, u'XMLRPC')
            self.assertEquals(system.activity[1].action, u'Changed')
            self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_devices(self):
        with session.begin():
            system = data_setup.create_system()
        self.server.push(system.fqdn, {'Devices': [{
            'type': 'IDE', 'bus': u'pci', 'driver': u'PIIX_IDE',
            'vendorID': '8086', 'deviceID': '7111',
            'description': u'82371AB/EB/MB PIIX4 IDE',
            'subsysVendorID': '0000', 'subsysDeviceID': '0000',
        }]})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Added')
            self.assertEquals(system.activity[0].field_name, u'Device')
            self.assertEquals(system.activity[0].old_value, None)
            # the new value will just be some random device id
            self.assertEquals(system.activity[1].service, u'XMLRPC')
            self.assertEquals(system.activity[1].action, u'Changed')
            self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_cpu(self):
        with session.begin():
            system = data_setup.create_system()
        self.server.push(system.fqdn, {'Cpu': {
            'modelName': 'Intel(R) Core(TM) i7 CPU       M 620  @ 2.67GHz',
            'vendor': 'GenuineIntel', 'family': 6, 'stepping': 5, 'model': 37,
            'processors': 4, 'cores': 4, 'sockets': 1, 'speed': 2659.708,
            'CpuFlags': ['fpu', 'mmx', 'syscall', 'ssse3'],
        }})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Changed')
            self.assertEquals(system.activity[0].field_name, u'CPU')
            self.assertEquals(system.activity[1].service, u'XMLRPC')
            self.assertEquals(system.activity[1].action, u'Changed')
            self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_numa(self):
        with session.begin():
            system = data_setup.create_system()
        self.server.push(system.fqdn, {'Numa': {'nodes': 321}})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Changed')
            self.assertEquals(system.activity[0].field_name, u'NUMA')
            self.assertEquals(system.activity[1].service, u'XMLRPC')
            self.assertEquals(system.activity[1].action, u'Changed')
            self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_disk(self):
        with session.begin():
            system=data_setup.create_system()
        self.server.push(system.fqdn, {'Disk': {'Disks': [{'model': 'Virtio Block Device',
                                                           'phys_sector_size': 512,
                                                           'sector_size': 512,
                                                           'size': str(8589934592)}]}})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Added')
            self.assertEquals(system.activity[0].field_name, 'Disk')

    # https://bugzilla.redhat.com/show_bug.cgi?id=708172
    def test_memory_is_updated(self):
        with session.begin():
            system = data_setup.create_system()
            system.memory = 4096
        self.server.push(system.fqdn, {'memory': '1024'})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.memory, 1024)

    def test_disk_is_updated(self):
        with session.begin():
            system = data_setup.create_system()

        testdict = dict(model='foo',
                        phys_sector_size=4096,
                        sector_size=4096,
                        size=str(500107837440))
        self.server.push(system.fqdn, dict(Disk=dict(Disks=[testdict])))
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.disks[0].model, testdict['model'])
            self.assertEquals(system.disks[0].size, int(testdict['size']))
            self.assertEquals(system.disks[0].sector_size, testdict['sector_size'])
            self.assertEquals(system.disks[0].phys_sector_size,
                    testdict['phys_sector_size'])

        # make sure we can update a system with existing disks
        testdict['model'] = 'newer'
        self.server.push(system.fqdn, dict(Disk=dict(Disks=[testdict])))
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.disks[0].model, testdict['model'])

    def test_hypervisor_none(self):
        with session.begin():
            system = data_setup.create_system()
            system.hypervisor = Hypervisor.by_name(u'KVM')
        self.server.push(system.fqdn, {'Hypervisor': None})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.hypervisor, None)
            self.assertEquals(system.activity[0].service, u'XMLRPC')
            self.assertEquals(system.activity[0].action, u'Changed')
            self.assertEquals(system.activity[0].field_name, u'Hypervisor')
            self.assertEquals(system.activity[0].old_value, u'KVM')
            self.assertEquals(system.activity[0].new_value, None)
            self.assertEquals(system.activity[1].service, u'XMLRPC')
            self.assertEquals(system.activity[1].action, u'Changed')
            self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_hypervisor_kvm(self):
        with session.begin():
            system = data_setup.create_system()
            system.hypervisor = None
        self.server.push(system.fqdn, {'Hypervisor': u'KVM'})
        with session.begin():
            session.refresh(system)
            self.assertEquals(system.hypervisor.hypervisor, u'KVM')

    # just check we don't raise an exception
    def test_set_bogus_property(self):
        with session.begin():
            system = data_setup.create_system()
        self.server.push(system.fqdn, {'Bothria': 8})

    # https://bugzilla.redhat.com/show_bug.cgi?id=841398
    def test_device_with_no_class(self):
        with session.begin():
            system1 = data_setup.create_system()
            system2 = data_setup.create_system()
        device_data = {'Devices': [{
            'type': None, 'bus': u'pci', 'driver': u'noclass',
            'description': u'Oh so very tacky',
            'vendorID': None, 'deviceID': None,
            'subsysVendorID': None, 'subsysDeviceID': None,
        }]}
        self.server.push(system1.fqdn, device_data)
        # DeviceClass('NONE') already exists now, so do it again
        # and check that nothing blows up
        self.server.push(system2.fqdn, device_data)

class SystemHistoryXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    def test_can_fetch_history(self):
        with session.begin():
            owner = data_setup.create_user()
            system = data_setup.create_system(owner=owner)
            system.activity.append(SystemActivity(user=owner, service=u'WEBUI',
                    action=u'Changed', field_name=u'fqdn',
                    old_value=u'oldname.example.com', new_value=system.fqdn))
        result = self.server.systems.history(system.fqdn)
        self.assertEquals(len(result), 1)
        assert_datetime_within(result[0]['created'],
                datetime.timedelta(seconds=5),
                reference=datetime.datetime.utcnow())
        self.assertEquals(result[0]['user'], owner.user_name)
        self.assertEquals(result[0]['service'], u'WEBUI')
        self.assertEquals(result[0]['action'], u'Changed')
        self.assertEquals(result[0]['field_name'], u'fqdn')
        self.assertEquals(result[0]['old_value'], u'oldname.example.com')
        self.assertEquals(result[0]['new_value'], system.fqdn)

    def test_fetches_history_since_timestamp(self):
        with session.begin():
            owner = data_setup.create_user()
            system = data_setup.create_system(owner=owner)
            # a recent one, which will be fetched
            system.activity.append(SystemActivity(user=owner, service=u'WEBUI',
                    action=u'Changed', field_name=u'fqdn',
                    old_value=u'oldname.example.com', new_value=system.fqdn))
            # an old one, which will not be fetched
            system.activity.append(SystemActivity(user=owner,
                    service=u'WEBUI', action=u'Changed', field_name=u'fqdn',
                    old_value=u'evenoldername.example.com',
                    new_value=u'oldname.example.com'))
            system.activity[-1].created = datetime.datetime(2005, 8, 16, 12, 23, 34)
        result = self.server.systems.history(system.fqdn,
                xmlrpclib.DateTime('20060101T00:00:00'))
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['old_value'], u'oldname.example.com')
