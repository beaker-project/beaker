
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
from bkr.inttest import data_setup, stub_cobbler
from bkr.server.model import User, Cpu, Key, Key_Value_String, Key_Value_Int, \
        System, SystemActivity, Provision, Hypervisor, SSHPubKey
from bkr.server.tools import beakerd

class ReserveSystemXmlRpcTest(XmlRpcTestCase):

    def test_cannot_reserve_when_not_logged_in(self):
        system = data_setup.create_system()
        session.flush()
        server = self.get_server()
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_('turbogears.identity.exceptions.IdentityFailure'
                    in e.faultString, e.faultString)

    def test_cannot_reserve_automated_system(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('Cannot reserve system with status Automated'
                    in e.faultString)

    def test_cannot_reserve_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(owner=user, status=u'Manual', shared=True)
        system.user = User.by_user_name(data_setup.ADMIN_USER)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('bkr.common.bexceptions.BX' in e.faultString,
                    e.faultString)

    def test_reserve_system(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        self.assert_(system.user is None)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
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
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        self.assert_(system.user is None)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.reserve(system.fqdn)
        try:
            server.systems.reserve(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('has already reserved system' in e.faultString)

    def test_reserve_via_external_service(self):
        service_group = data_setup.create_group(permissions=[u'proxy_auth'])
        service_user = data_setup.create_user(password=u'password')
        data_setup.add_user_to_group(service_user, service_group)
        user = data_setup.create_user(password=u'notused')
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        self.assert_(system.user is None)
        session.flush()
        server = self.get_server()
        server.auth.login_password(service_user.user_name, 'password',
                user.user_name)
        server.systems.reserve(system.fqdn)
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

    def test_cannot_release_when_not_logged_in(self):
        system = data_setup.create_system()
        session.flush()
        server = self.get_server()
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except Exception, e:
            self.assert_('turbogears.identity.exceptions.IdentityFailure'
                    in e.faultString, e.faultString)

    def test_cannot_release_when_not_current_user(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system.reserve(service=u'testdata', user=other_user)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is reserved by a different user'
                    in e.faultString)

    def test_release_system(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        system.reserve(service=u'testdata', user=user)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
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
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        system.reserve(service=u'testdata', user=user)
        session.flush()
        server = self.get_server()
        server.auth.login_password(user.user_name, 'password')
        server.systems.release(system.fqdn)
        try:
            server.systems.release(system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is not reserved' in e.faultString)

class SystemPowerXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.stub_cobbler_thread.start()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        session.flush()
        self.server = self.get_server()

    def tearDown(self):
        self.stub_cobbler_thread.stop()

    def test_cannot_power_when_not_logged_in(self):
        try:
            self.server.systems.power('on', 'fqdn')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('turbogears.identity.exceptions.IdentityFailure'
                    in e.faultString, e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_cannot_power_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = other_user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.power('on', system.fqdn)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('System is in use' in e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def check_power_action(self, action):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system()
        data_setup.configure_system_power(system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        system.lab_controller = self.lab_controller
        system.user = None
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power(action, system.fqdn)
        self.assertEqual(
                System.by_fqdn(system.fqdn, user).command_queue[0].action,
                action)
        beakerd.queued_commands()
        self.assertEqual(self.stub_cobbler_thread.cobbler.systems[system.fqdn],
                {'power_type': 'drac',
                 'power_address': 'nowhere.example.com',
                 'power_user': 'teh_powz0r',
                 'power_pass': 'onoffonoff',
                 'power_id': 'asdf'})

    def test_power_on(self):
        self.check_power_action('on')

    def test_power_off(self):
        self.check_power_action('off')

    def test_reboot(self):
        self.check_power_action('reboot')

    def test_can_force_powering_system_in_use(self):
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system = data_setup.create_system()
        data_setup.configure_system_power(system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        system.lab_controller = self.lab_controller
        system.user = other_user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power('on', system.fqdn, False, True)
        self.assertEqual(
                System.by_fqdn(system.fqdn, user).command_queue[0].action,
                'on')
        beakerd.queued_commands()

    def test_clear_netboot(self):
        user = data_setup.create_user(password=u'password')
        system = data_setup.create_system()
        data_setup.configure_system_power(system)
        system.lab_controller = self.lab_controller
        system.user = None
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.power('reboot', system.fqdn, True)
        self.assertEqual(
                System.by_fqdn(system.fqdn, user).command_queue[0].action,
                'reboot')
        beakerd.queued_commands()
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.systems[system.fqdn]['netboot-enabled'],
                False)

class SystemProvisionXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        self.distro = data_setup.create_distro(arch=u'i386')
        self.usable_system = data_setup.create_system(arch=u'i386',
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        data_setup.configure_system_power(self.usable_system, power_type=u'drac',
                address=u'nowhere.example.com', user=u'teh_powz0r',
                password=u'onoffonoff', power_id=u'asdf')
        self.usable_system.lab_controller = self.lab_controller
        self.usable_system.user = data_setup.create_user(password=u'password')
        self.usable_system.provisions[self.distro.arch] = Provision(
                arch=self.distro.arch,
                kernel_options='ksdevice=eth0 console=ttyS0')
        session.flush()
        self.stub_cobbler_thread.start()
        self.server = self.get_server()

    def tearDown(self):
        self.stub_cobbler_thread.stop()

    def test_cannot_provision_when_not_logged_in(self):
        try:
            self.server.systems.provision('fqdn', 'distro')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('turbogears.identity.exceptions.IdentityFailure'
                    in e.faultString, e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_cannot_provision_automated_system(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Automated', shared=True)
        user = data_setup.create_user(password=u'password')
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, 'distro')
        except xmlrpclib.Fault, e:
            # It's not really a permissions issue, but oh well
            self.assert_('has insufficient permissions to provision'
                    in e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_cannot_provision_system_in_use(self):
        system = data_setup.create_system(
                owner=User.by_user_name(data_setup.ADMIN_USER),
                status=u'Manual', shared=True)
        user = data_setup.create_user(password=u'password')
        other_user = data_setup.create_user()
        system.user = other_user
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        try:
            self.server.systems.provision(system.fqdn, 'distro')
        except xmlrpclib.Fault, e:
            self.assert_('Reserve a system before provisioning'
                    in e.faultString)
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_provision(self):
        kickstart = '''
            %%pre
            kickstart lol!
            do some stuff etc
            '''
        system = self.usable_system
        self.server.auth.login_password(system.user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro.install_name,
                'method=nfs',
                'noapic',
                'noapic runlevel=3',
                kickstart)
        beakerd.queued_commands()
        kickstart_filename = '/var/lib/cobbler/kickstarts/%s.ks' % system.fqdn
        self.assertEqual(self.stub_cobbler_thread.cobbler.systems[system.fqdn],
                {'power_type': 'drac',
                 'power_address': 'nowhere.example.com',
                 'power_user': 'teh_powz0r',
                 'power_pass': 'onoffonoff',
                 'power_id': 'asdf',
                 'ksmeta': {'method': 'nfs'},
                 'kopts': {'ksdevice': 'eth0', 'noapic': None, 'console': 'ttyS0'},
                 'kopts_post': {'noapic': None, 'runlevel': '3'},
                 'profile': self.distro.install_name,
                 'kickstart': kickstart_filename,
                 'netboot-enabled': True})
        self.assert_(kickstart in
                self.stub_cobbler_thread.cobbler.kickstarts[kickstart_filename])
        self.assertEqual(
                self.stub_cobbler_thread.cobbler.system_actions[system.fqdn],
                'reboot')

    def test_provision_without_reboot(self):
        self.server.auth.login_password(self.usable_system.user.user_name,
                'password')
        self.server.systems.provision(self.usable_system.fqdn,
                self.distro.install_name, None, None, None, None,
                False) # this last one is reboot=False
        self.assert_(not self.stub_cobbler_thread.cobbler.system_actions)

    def test_refuses_to_provision_distro_with_mismatched_arch(self):
        distro = data_setup.create_distro(arch=u'x86_64')
        session.flush()
        self.server.auth.login_password(self.usable_system.user.user_name,
                'password')
        try:
            self.server.systems.provision(self.usable_system.fqdn, distro.install_name)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('cannot be provisioned on system' in e.faultString)

    def test_refuses_to_provision_distro_not_in_lc(self):
        for lca in self.distro.lab_controller_assocs:
            session.delete(lca)
        session.flush()
        self.server.auth.login_password(self.usable_system.user.user_name,
                'password')
        try:
            self.server.systems.provision(self.usable_system.fqdn, self.distro.install_name)
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('cannot be provisioned on system' in e.faultString)

    def test_kernel_options_inherited_from_defaults(self):
        system = self.usable_system
        self.server.auth.login_password(system.user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro.install_name,
                None, 'ksdevice=eth1')
        # console=ttyS0 comes from arch default, created in setUp()
        kopts = self.stub_cobbler_thread.cobbler.systems[system.fqdn]['kopts']
        self.assertEqual(kopts, {'ksdevice': 'eth1', 'console': 'ttyS0'})

    def test_provision_user_ssh_keys(self):
        system = self.usable_system
        user = system.user
        k = SSHPubKey(u'ssh-rsa',
                      u'AAAAB3NzaC1yc2EAAAADAQABAAAAgQDX92WltLUTlGgRngO4k68cE8fH88cpJPpXRE'\
                      'hXthaIoooFds7MeAOu3+UU5wYmmpz/q4FykmBc1PFP2M7aS2i4X/sGZmP57il5yfUK'\
                      'SJtlhJamBPwgoeg/PBvERbIdRtbAq8NMO7mAt+zuU9fWCs/fYEJDva3D0UZsY/Qpt+'\
                      '4mBw==', u'man@moon')
        user.sshpubkeys.append(k)
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro.install_name,
                'method=nfs', 'noapic', 'noapic runlevel=3', '')
        snippet_filename = '/var/lib/cobbler/snippets/per_system/ks_appends/%s' % system.fqdn
        self.assert_('man@moon' in
                self.stub_cobbler_thread.cobbler.snippets[snippet_filename])

    def test_provision_root_password(self):
        system = self.usable_system
        user = system.user
        user.root_password = 'gyfrinachol'
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.provision(system.fqdn, self.distro.install_name,
                'method=nfs', 'noapic', 'noapic runlevel=3', '')
        self.assert_(crypt.crypt('gyfrinachol', user.root_password) ==
                     self.stub_cobbler_thread.cobbler.systems[system.fqdn]['ksmeta']['password'])

    def test_ssh_key_ksappend_has_end(self):
        system = self.usable_system
        user = system.user
        user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'AAAAxyz', u'abc@def'))
        distro = data_setup.create_distro(name='RedHatEnterpriseLinux7.8.9', arch=u'i386',
                                          osmajor=u'RedHatEnterpriseLinux7')
        session.flush()
        self.server.auth.login_password(user.user_name, 'password')
        self.server.systems.provision(system.fqdn, distro.install_name)
        beakerd.queued_commands()
        snippet_filename = '/var/lib/cobbler/snippets/per_system/ks_appends/%s' % system.fqdn
        print self.stub_cobbler_thread.cobbler.snippets[snippet_filename]
        self.assert_('%end' in self.stub_cobbler_thread.cobbler.snippets[snippet_filename])

class LegacyPushXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=658503
    def test_system_activity_shows_changes(self):
        system = data_setup.create_system()
        system.key_values_string.extend([
            Key_Value_String(Key.by_name(u'PCIID'), '1022:2000'),
            Key_Value_String(Key.by_name(u'PCIID'), '80ee:beef'),
        ])
        session.flush()
        self.server.legacypush(system.fqdn,
                {'PCIID': ['80ee:cafe', '80ee:beef']})
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
        system = data_setup.create_system()
        system.key_values_string.append(
                Key_Value_String(Key.by_name(u'HVM'), '0'))
        session.flush()

        self.server.legacypush(system.fqdn, {'HVM': False})
        session.refresh(system)
        self.assertEquals(len(system.activity), 0) # nothing has changed, yet

        self.server.legacypush(system.fqdn, {'HVM': True})
        session.refresh(system)
        self.assertEquals(system.activity[0].field_name, u'Key/Value')
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Added')
        self.assertEquals(system.activity[0].old_value, None)
        self.assertEquals(system.activity[0].new_value, u'HVM/1')

    # https://bugzilla.redhat.com/show_bug.cgi?id=665441
    def test_existing_keys_are_untouched(self):
        system = data_setup.create_system()
        system.key_values_string.extend([
            Key_Value_String(Key.by_name(u'PCIID'), '1022:2000'), # this one gets deleted
            Key_Value_String(Key.by_name(u'HVM'), '0'), # this one gets updated
            Key_Value_String(Key.by_name(u'VENDOR'), 'Bob'), # this one should not be touched
        ])
        session.flush()

        self.server.legacypush(system.fqdn, {'PCIID': [], 'HVM': True})
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
        system = data_setup.create_system()
        system.vendor = None
        system.model = None
        system.memory = None
        session.flush()
        self.server.push(system.fqdn,
                {'vendor': 'Acorn', 'model': 'Archimedes', 'memory': '16'})
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
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Arch': ['sparc32']})
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
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Devices': [{
            'type': 'IDE', 'bus': u'pci', 'driver': u'PIIX_IDE',
            'vendorID': '8086', 'deviceID': '7111',
            'description': u'82371AB/EB/MB PIIX4 IDE',
            'subsysVendorID': '0000', 'subsysDeviceID': '0000',
        }]})
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
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Cpu': {
            'modelName': 'Intel(R) Core(TM) i7 CPU       M 620  @ 2.67GHz',
            'vendor': 'GenuineIntel', 'family': 6, 'stepping': 5, 'model': 37,
            'processors': 4, 'cores': 4, 'sockets': 1, 'speed': 2659.708,
            'CpuFlags': ['fpu', 'mmx', 'syscall', 'ssse3'],
        }})
        session.refresh(system)
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Changed')
        self.assertEquals(system.activity[0].field_name, u'CPU')
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Changed')
        self.assertEquals(system.activity[1].field_name, u'checksum')

    def test_system_activity_shows_changes_for_numa(self):
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Numa': {'nodes': 321}})
        session.refresh(system)
        self.assertEquals(system.activity[0].service, u'XMLRPC')
        self.assertEquals(system.activity[0].action, u'Changed')
        self.assertEquals(system.activity[0].field_name, u'NUMA')
        self.assertEquals(system.activity[1].service, u'XMLRPC')
        self.assertEquals(system.activity[1].action, u'Changed')
        self.assertEquals(system.activity[1].field_name, u'checksum')

    # https://bugzilla.redhat.com/show_bug.cgi?id=708172
    def test_memory_is_updated(self):
        system = data_setup.create_system()
        system.memory = 4096
        session.flush()
        self.server.push(system.fqdn, {'memory': '1024'})
        session.refresh(system)
        self.assertEquals(system.memory, 1024)

    def test_hypervisor_none(self):
        system = data_setup.create_system()
        system.hypervisor = Hypervisor.by_name(u'KVM')
        session.flush()
        self.server.push(system.fqdn, {'Hypervisor': None})
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
        system = data_setup.create_system()
        system.hypervisor = None
        session.flush()
        self.server.push(system.fqdn, {'Hypervisor': u'KVM'})
        session.refresh(system)
        self.assertEquals(system.hypervisor.hypervisor, u'KVM')

    # just check we don't raise an exception
    def test_set_bogus_property(self):
        system = data_setup.create_system()
        session.flush()
        self.server.push(system.fqdn, {'Bothria': 8})

class SystemHistoryXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    def test_can_fetch_history(self):
        owner = data_setup.create_user()
        system = data_setup.create_system(owner=owner)
        system.activity.append(SystemActivity(user=owner, service=u'WEBUI',
                action=u'Changed', field_name=u'fqdn',
                old_value=u'oldname.example.com', new_value=system.fqdn))
        session.flush()
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
        session.flush()
        result = self.server.systems.history(system.fqdn,
                xmlrpclib.DateTime('20060101T00:00:00'))
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['old_value'], u'oldname.example.com')
