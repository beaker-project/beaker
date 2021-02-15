
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import re
import time
import datetime
import unittest
import pkg_resources
import shutil
import urlparse
import lxml.etree
import email
from decimal import Decimal
from mock import patch
import inspect
import kid
from turbogears.database import session
from bkr.server.installopts import InstallOptions
from bkr.server import model, identity
from bkr.server.app import app
from bkr.server.model import System, SystemStatus, SystemActivity, TaskStatus, \
        SystemType, Job, JobCc, Key, Key_Value_Int, Key_Value_String, \
        Cpu, Numa, Provision, Arch, DistroTree, \
        LabControllerDistroTree, TaskType, TaskPackage, Device, DeviceClass, \
        GuestRecipe, GuestResource, Recipe, LogRecipe, RecipeResource, \
        VirtResource, OSMajor, OSMajorInstallOptions, Watchdog, RecipeSet, \
        RecipeVirtStatus, MachineRecipe, GuestRecipe, Disk, Task, TaskResult, \
        Group, User, ActivityMixin, SystemAccessPolicy, SystemPermission, \
        RecipeTask, RecipeTaskResult, DeclarativeMappedObject, OSVersion, \
        RecipeReservationRequest, ReleaseAction, SystemPool, CommandStatus, \
        GroupMembershipType, RecipeSetComment, Power, LogRecipeTask, \
        LogRecipeTaskResult

from bkr.server.bexceptions import BeakerException
from sqlalchemy.sql import not_
from sqlalchemy.exc import OperationalError, IntegrityError
import netaddr
from bkr.inttest import data_setup, DatabaseTestCase, get_server_base
from bkr.inttest.assertions import assert_datetime_within
import turbogears
import os
import dnf
import tempfile

def serialize_kid_element(elem):
    return kid.XHTMLSerializer().serialize(kid.ElementStream(elem), fragment=True)

class SchemaSanityTest(DatabaseTestCase):

    def test_all_tables_use_innodb(self):
        engine = DeclarativeMappedObject.metadata.bind
        if engine.url.drivername != 'mysql':
            raise unittest.SkipTest('not using MySQL')
        for table in engine.table_names():
            # We don't control the creation of alembic_version, so if the
            # server default is MyISAM alembic_version will end up using that.
            # It doesn't really matter though.
            if table == 'alembic_version':
                continue
            engine_used = engine.scalar(
                    'SELECT engine FROM information_schema.tables '
                    'WHERE table_schema = DATABASE() AND table_name = %s',
                    table)
            self.assertEquals(engine_used, 'InnoDB',
                    'MySQL storage engine for table %s should be InnoDB' % table)

class ModelInitializationTest(DatabaseTestCase):

    # We are testing the database creation done by bkr.server.tools.init.
    # However do not actually invoke that here, because it would be too
    # complicated to set up properly. Instead we just test the initialization
    # that was done by bkr.inttest.setup_package for this test run.

    def test_admin_user_owns_admin_group(self):
        admin_user = User.by_user_name(data_setup.ADMIN_USER)
        admin_group = Group.by_name(u'admin')
        self.assertTrue(admin_group.has_owner(admin_user))

class ActivityMixinTest(DatabaseTestCase):

    def test_field_names_correct(self):
        # Ensure ActivityMixin._fields stays in sync with the parameters
        # accepted by ActivityMixin._record_activity_inner
        argspec = inspect.getargspec(ActivityMixin._record_activity_inner)
        params = tuple(argspec[0][1:]) # skip 'self'
        self.assertEqual(ActivityMixin._fields, ('object_id',) + params)

    def test_log_formatting(self):
        # Ensure ActivityMixin._log_fmt works as expected
        entries = dict((v, k) for k, v in enumerate(ActivityMixin._fields))
        entries['kind'] = 'ActivityKind'
        text = ActivityMixin._log_fmt % entries
        self.assert_(text.startswith('Tentative ActivityKind:'))
        entries.pop('kind')
        for name, value in entries.items():
            self.assert_(('%s=%r' % (name, value)) in text, text)


class TestSystem(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_create_system_params(self):
        owner = data_setup.create_user()
        new_system = System(fqdn=u'test-fqdn', contact=u'test@email.com',
                            location=u'Brisbane', model=u'Proliant', serial=u'4534534',
                            vendor=u'Dell', type=SystemType.machine,
                            status=SystemStatus.automated,
                            lab_controller=data_setup.create_labcontroller(),
                            owner=owner)
        session.flush()
        self.assertEqual(new_system.fqdn, 'test-fqdn')
        self.assertEqual(new_system.contact, 'test@email.com')
        self.assertEqual(new_system.location, 'Brisbane')
        self.assertEqual(new_system.model, 'Proliant')
        self.assertEqual(new_system.serial, '4534534')
        self.assertEqual(new_system.vendor, 'Dell')
        self.assertEqual(new_system.owner, owner)

    def test_add_user_to_system(self):
        user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = user
        session.flush()
        self.assertEquals(system.user, user)

    def test_remove_user_from_system(self):
        user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = user
        system.user = None
        session.flush()
        self.assert_(system.user is None)

    def test_install_options_override(self):
        distro_tree = data_setup.create_distro_tree()
        osmajor = distro_tree.distro.osversion.osmajor
        OSMajorInstallOptions(osmajor=osmajor, arch=distro_tree.arch,
                kernel_options='serial')
        system = data_setup.create_system()
        system.provisions[distro_tree.arch] = Provision(arch=distro_tree.arch,
                kernel_options='console=ttyS0 ksdevice=eth0 vnc')
        opts = system.manual_provision_install_options(distro_tree).combined_with(
                InstallOptions.from_strings('', u'ksdevice=eth1 !vnc', ''))
        # ksdevice should be overriden but console should be inherited
        # noverifyssl comes from server-test.cfg
        # serial comes from the osmajor
        # vnc should be removed
        self.assertEqual(opts.kernel_options,
                dict(console='ttyS0', ksdevice='eth1', noverifyssl=None,
                     serial=None, netbootloader='pxelinux.0'))

    def test_mark_broken_updates_history(self):
        system = data_setup.create_system(status = SystemStatus.automated,
                                          lab_controller=data_setup.create_labcontroller())
        system.mark_broken(reason = "Attacked by cyborgs")
        session.flush()
        system_activity = system.dyn_activity.filter(SystemActivity.field_name == u'Status').first()
        self.assertEqual(system_activity.old_value, u'Automated')
        self.assertEqual(system_activity.new_value, u'Broken')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1037878
    def test_invalid_fqdn(self):
        system = data_setup.create_system()
        try:
            system.fqdn = ''
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('System must have an associated FQDN', str(e))
        try:
            system.fqdn = 'invalid_system_fqdn'
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('Invalid FQDN for system', str(e))

    def test_invalid_power_address(self):
        system = data_setup.create_system()
        system.power = Power()
        try:
            system.power.power_address = u''
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('Power address is required', str(e))

    def test_invalid_power_quiescent_period(self):
        system = data_setup.create_system()
        system.power = Power()
        try:
            system.power.power_quiescent_period = -1
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('Quiescent period for power control must be greater'
                    ' than or equal to zero', str(e))

    def test_cannot_set_status_reason_when_system_is_not_bad(self):
        system = data_setup.create_system(status=SystemStatus.automated,
                                          lab_controller=data_setup.create_labcontroller())
        try:
            system.status_reason = u'Currently is broken'
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('Cannot set status reason when status is %s' % SystemStatus.automated,
                    str(e))

    def test_distros(self):
        lc = data_setup.create_labcontroller()
        excluded_osmajor = OSMajor.lazy_create(
                osmajor=data_setup.unique_name(u'osmajor_test_distros%s'))
        tree_excluded = data_setup.create_distro_tree(arch=u'i386',
                osmajor=excluded_osmajor.osmajor)
        included_osmajor = OSMajor.lazy_create(
                osmajor=data_setup.unique_name(u'osmajor_test_distros%s'))
        tree_not_in_lab = data_setup.create_distro_tree(arch=u'i386',
                osmajor=included_osmajor.osmajor, lab_controllers=[])
        tree_in_lab = data_setup.create_distro_tree(arch=u'i386',
                osmajor=included_osmajor.osmajor, lab_controllers=[lc])
        system = data_setup.create_system(arch=u'i386', lab_controller=lc,
                exclude_osmajor=[excluded_osmajor])
        session.flush()
        distros = system.distros()
        self.assertNotIn(tree_excluded.distro, distros)
        self.assertNotIn(tree_not_in_lab.distro, distros)
        self.assertIn(tree_in_lab.distro, distros)

    def test_create_system_multi_arch(self):
        excluded_osmajor = OSMajor.lazy_create(
            osmajor=data_setup.unique_name(u'osmajor_test_distros%s'))
        tree_excluded_1 = data_setup.create_distro_tree(arch=u'i386',
                                                        osmajor=excluded_osmajor.osmajor)
        tree_excluded_2 = data_setup.create_distro_tree(arch=u'x86_64',
                                                        osmajor=excluded_osmajor.osmajor)
        system = data_setup.create_system(arch=[u'i386', u'x86_64'],
                                          exclude_osmajor=[excluded_osmajor])
        session.flush()
        distros = system.distros()
        self.assertNotIn(tree_excluded_1.distro, distros)
        self.assertNotIn(tree_excluded_2.distro, distros)

    def test_system_using_pool_access_policy(self):
        system1 = data_setup.create_system(shared=False)
        pool = data_setup.create_system_pool(name=u'pool-1',
                                             systems=[system1])
        pool_policy = pool.access_policy
        perm1 = SystemPermission.reserve
        user = data_setup.create_user()
        pool_policy.add_rule(perm1, user=user)
        user1 = data_setup.create_user()

        pool_policy.add_rule(SystemPermission.edit_policy, user=user1)
        pool_policy.add_rule(SystemPermission.edit_system, user=user1)
        pool_policy.add_rule(SystemPermission.view_power, user=user1)
        pool_policy.add_rule(SystemPermission.loan_any, user=user1)
        pool_policy.add_rule(SystemPermission.loan_self, user=user1)
        pool_policy.add_rule(SystemPermission.reserve, user=user1)
        pool_policy.add_rule(SystemPermission.control_system, user=user1)

        session.flush()

        self.assertFalse(system1.can_edit(user1))
        self.assertFalse(system1.can_edit_policy(user1))
        self.assertFalse(system1.can_view_power(user1))
        self.assertFalse(system1.can_lend(user1))
        self.assertFalse(system1.can_borrow(user1))
        self.assertFalse(system1.can_reserve(user1))
        self.assertFalse(system1.can_power(user1))
        self.assertFalse(system1.can_configure_netboot(user1))

        # assign the pool policy
        system1.active_access_policy = pool_policy

        self.assertTrue(system1.can_edit(user1))
        self.assertTrue(system1.can_edit_policy(user1))
        self.assertTrue(system1.can_edit(user1))
        self.assertTrue(system1.can_edit_policy(user1))
        self.assertTrue(system1.can_view_power(user1))
        self.assertTrue(system1.can_lend(user1))
        self.assertTrue(system1.can_borrow(user1))
        self.assertTrue(system1.can_reserve(user1))
        self.assertTrue(system1.can_power(user1))
        self.assertFalse(system1.can_configure_netboot(user1))


class TestSystemPool(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_create_system_pool(self):
        system1 = data_setup.create_system()
        system2 = data_setup.create_system()
        data_setup.create_system_pool(name=u'pool-1',
                                      systems=[system1, system2])
        session.flush()
        pool = SystemPool.by_name(u'pool-1')
        self.assertEquals(pool.name, u'pool-1')
        self.assertIn(system1, pool.systems)
        self.assertIn(system2, pool.systems)

        # invalid pool name should raise ValueError
        self.assertRaises(ValueError, lambda: data_setup.create_system_pool(name=u'pool-1/'))

    def test_system_pool_owner(self):
        user1 = data_setup.create_user()
        pool = data_setup.create_system_pool(owning_user=user1)
        session.flush()
        self.assertEquals(pool.owner, user1)

        # change owner to group
        group = data_setup.create_group()
        pool.owning_user = None
        pool.owning_group = group
        session.flush()
        self.assertEquals(pool.owner, group)
        self.assertFalse(pool.has_owner(user1))

        # check ownership
        group.add_member(user1)
        session.flush()
        self.assertTrue(pool.has_owner(user1))

    def test_pool_permissions(self):
        pool = data_setup.create_system_pool(name=u'pool-1')
        pool_policy = pool.access_policy
        user1 = data_setup.create_user()
        other_user = data_setup.create_user()
        pool_policy.add_rule(SystemPermission.edit_policy, user=user1)

        session.flush()
        self.assert_(SystemAccessPolicy.query
                     .filter(SystemAccessPolicy.id == pool_policy.id)
                     .filter(SystemAccessPolicy.grants(user1, SystemPermission.edit_policy)).count())
        self.assertTrue(pool.can_edit_policy(user1))
        self.assertFalse(pool.can_edit_policy(other_user))

    def test_system_pool_access_policy_deletion(self):
        system1 = data_setup.create_system()
        pool = data_setup.create_system_pool(name=u'pool-1')
        policy = pool.access_policy
        perm = SystemPermission.reserve
        user = data_setup.create_user()
        policy.add_rule(perm, user=user)

        session.flush()
        self.assertEquals(len(policy.rules), 2)
        self.assertTrue(policy.grants(user, perm))
        # assign the pool policy to the system
        system1.active_access_policy = policy
        self.assertTrue(system1.active_access_policy.grants(user, perm))

        # deleting the system should not delete the pool policy
        session.flush()
        session.delete(system1)
        session.flush()
        session.refresh(pool)
        self.assertTrue(pool.access_policy.grants(user, perm))


class SystemFilterMethodsTest(DatabaseTestCase):
    """
    Test cases for the hybrid methods/properties used to build system queries.
    """

    def setUp(self):
        session.begin()
        self.addCleanup(session.rollback)

    def check_hybrid(self, base_query, func, included, excluded):
        session.flush()
        query = base_query.filter(func(System))
        if included:
            # check that the query matches all included systems
            self.assertItemsEqual(included,
                    query.filter(System.id.in_([s.id for s in included])).all())
            # check that the method returns true for all included systems
            for system in included:
                self.assertTrue(func(system))
        if excluded:
            # check that the query matches no excluded systems
            self.assertItemsEqual([],
                    query.filter(System.id.in_([s.id for s in excluded])).all())
            # check that the method returns false for all excluded systems
            for system in excluded:
                self.assertFalse(func(system))

    def test_visible_to_anonymous(self):
        private = data_setup.create_system(private=True)
        public = data_setup.create_system(private=False)
        self.check_hybrid(
                System.query.outerjoin(System.custom_access_policy),
                lambda s: s.visible_to_anonymous,
                included=[public], excluded=[private])

    def test_visible_to_user(self):
        private = data_setup.create_system(private=True)
        public = data_setup.create_system(private=False)
        self.check_hybrid(
                System.query.outerjoin(System.custom_access_policy),
                lambda s: s.visible_to_user(private.owner),
                included=[public, private], excluded=[])
        other_user = data_setup.create_user()
        self.check_hybrid(
                System.query.outerjoin(System.custom_access_policy),
                lambda s: s.visible_to_user(other_user),
                included=[public], excluded=[private])

    def test_is_free(self):
        lc = data_setup.create_labcontroller()
        disabled_lc = data_setup.create_labcontroller()
        disabled_lc.disabled = True
        user = data_setup.create_user()
        reserved = data_setup.create_system(lab_controller=lc)
        reserved.user = user
        reserved_by_other = data_setup.create_system(lab_controller=lc)
        reserved_by_other.user = data_setup.create_user()
        loaned = data_setup.create_system(lab_controller=lc)
        loaned.loaned = user
        loaned_to_other = data_setup.create_system(lab_controller=lc)
        loaned_to_other.loaned = data_setup.create_user()
        attached_to_disabled_lc = data_setup.create_system(
                lab_controller=disabled_lc)
        not_reserved_not_loaned = data_setup.create_system(lab_controller=lc)
        self.check_hybrid(System.all(user),
                lambda s: s.is_free(user),
                included=[not_reserved_not_loaned, loaned],
                excluded=[reserved, reserved_by_other, loaned_to_other,
                          attached_to_disabled_lc])

    def test_compatible_with_distro_tree(self):
        distro_tree = data_setup.create_distro_tree(arch=u'x86_64')
        wrong_arch = data_setup.create_system(arch=u'i386')
        osmajor_excluded = data_setup.create_system(arch=u'x86_64',
                exclude_osmajor=[distro_tree.distro.osversion.osmajor])
        osversion_excluded = data_setup.create_system(arch=u'x86_64',
                exclude_osversion=[distro_tree.distro.osversion])
        compatible = data_setup.create_system(arch=u'x86_64')
        self.check_hybrid(System.query,
                lambda s: s.compatible_with_distro_tree(arch=distro_tree.arch,
                                                        osmajor=distro_tree.distro.osversion.osmajor.osmajor,
                                                        osminor=distro_tree.distro.osversion.osminor),
                included=[compatible],
                excluded=[wrong_arch, osmajor_excluded, osversion_excluded])

    def test_in_lab_with_distro_tree(self):
        lc = data_setup.create_labcontroller()
        distro_tree = data_setup.create_distro_tree(lab_controllers=[lc])
        in_lab = data_setup.create_system(lab_controller=lc)
        in_wrong_lab = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller())
        in_no_lab = data_setup.create_system()
        in_no_lab.lab_controller = None
        self.check_hybrid(System.all(data_setup.create_user()),
                lambda s: s.in_lab_with_distro_tree(distro_tree),
                included=[in_lab], excluded=[in_wrong_lab, in_no_lab])

    def test_can_reserve(self):
        user = data_setup.create_user()
        owned = data_setup.create_system(owner=user)
        loaned = data_setup.create_system()
        loaned.loaned = user
        shared = data_setup.create_system(shared=True)
        not_shared = data_setup.create_system(shared=False)
        self.check_hybrid(System.all(user),
                lambda s: s.can_reserve(user),
                included=[owned, loaned, shared],
                excluded=[not_shared])

    #https://bugzilla.redhat.com/show_bug.cgi?id=1216257
    def test_diskcount(self):
        one_disk_system = data_setup.create_system()
        one_disk_system.disks[:] = [
                Disk(size=8000000000, sector_size=512, phys_sector_size=512)]
        two_disk_system = data_setup.create_system()
        two_disk_system.disks[:] = [
                Disk(size=500000000000, sector_size=512, phys_sector_size=512),
                Disk(size=8000000000, sector_size=4096, phys_sector_size=4096)]
        self.check_hybrid(System.query,
                lambda s: s.diskcount >= 2,
                included=[two_disk_system],
                excluded=[one_disk_system])


class TestSystemKeyValue(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_removing_key_type_cascades_to_key_value(self):
        # https://bugzilla.redhat.com/show_bug.cgi?id=647566
        string_key_type = Key(u'COLOUR', numeric=False)
        int_key_type = Key(u'FAIRIES', numeric=True)
        system = data_setup.create_system()
        system.key_values_string.append(
                Key_Value_String(string_key_type, u'pretty pink'))
        system.key_values_int.append(Key_Value_Int(int_key_type, 9000))
        session.flush()

        session.delete(string_key_type)
        session.delete(int_key_type)
        session.flush()

        session.expunge_all()
        reloaded_system = System.query.get(system.id)
        self.assertEqual(reloaded_system.key_values_string, [])
        self.assertEqual(reloaded_system.key_values_int, [])

class SystemPermissionsTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.owner = data_setup.create_user()
        self.admin = data_setup.create_admin()
        self.system = data_setup.create_system(owner=self.owner, shared=False)
        self.policy = self.system.custom_access_policy
        self.unprivileged = data_setup.create_user()

    def tearDown(self):
        session.rollback()

    # This ensures we "fail secure" if any code erroneously checks
    # permissions without ensure the user is authenticated first
    # For example, https://bugzilla.redhat.com/show_bug.cgi?id=1039514
    def test_no_anonymous_access(self):
        self.assertRaises(RuntimeError, self.system.can_change_owner, None)
        self.assertRaises(RuntimeError, self.system.can_edit_policy, None)
        self.assertRaises(RuntimeError, self.system.can_edit, None)
        self.assertRaises(RuntimeError, self.system.can_lend, None)
        self.assertRaises(RuntimeError, self.system.can_borrow, None)
        self.assertRaises(RuntimeError, self.system.can_return_loan, None)
        self.assertRaises(RuntimeError, self.system.can_reserve, None)
        self.assertRaises(RuntimeError, self.system.can_reserve_manually, None)
        self.assertRaises(RuntimeError, self.system.can_unreserve, None)
        self.assertRaises(RuntimeError, self.system.can_power, None)
        self.assertRaises(RuntimeError, self.system.can_configure_netboot, None)

    def test_can_change_owner(self):
        self.assertTrue(self.system.can_change_owner(self.owner))
        self.assertTrue(self.system.can_change_owner(self.admin))
        self.assertFalse(self.system.can_change_owner(self.unprivileged))
        # Check policy editing permission implies ability to change owner
        # https://bugzilla.redhat.com/show_bug.cgi?id=1063893
        editor = data_setup.create_user()
        self.policy.add_rule(SystemPermission.edit_policy, user=editor)
        self.assertTrue(self.system.can_change_owner(editor))
        # Check other users are unaffected
        self.assertTrue(self.system.can_change_owner(self.owner))
        self.assertTrue(self.system.can_change_owner(self.admin))
        self.assertFalse(self.system.can_change_owner(self.unprivileged))

    def test_can_edit_policy(self):
        # Default state
        self.assertTrue(self.system.can_edit_policy(self.owner))
        self.assertTrue(self.system.can_edit_policy(self.admin))
        self.assertFalse(self.system.can_edit_policy(self.unprivileged))
        # Check policy editing permission
        editor = data_setup.create_user()
        self.policy.add_rule(SystemPermission.edit_policy, user=editor)
        self.assertTrue(self.system.can_edit_policy(editor))
        # Check other users are unaffected
        self.assertTrue(self.system.can_edit_policy(self.owner))
        self.assertTrue(self.system.can_edit_policy(self.admin))
        self.assertFalse(self.system.can_edit_policy(self.unprivileged))

    def test_can_edit(self):
        # Default state
        self.assertTrue(self.system.can_edit(self.owner))
        self.assertTrue(self.system.can_edit(self.admin))
        self.assertFalse(self.system.can_edit(self.unprivileged))
        # Check system editing permission
        editor = data_setup.create_user()
        self.policy.add_rule(SystemPermission.edit_system, user=editor)
        self.assertTrue(self.system.can_edit(editor))
        # Check other users are unaffected
        self.assertTrue(self.system.can_edit(self.owner))
        self.assertTrue(self.system.can_edit(self.admin))
        self.assertFalse(self.system.can_edit(self.unprivileged))

    def check_lending_permissions(self, allow=(), deny=()):
        self.assertTrue(self.system.can_lend(self.owner))
        self.assertTrue(self.system.can_lend(self.admin))
        self.assertFalse(self.system.can_lend(self.unprivileged))
        for user in allow:
            msg = "%s cannot lend system"
            self.assertTrue(self.system.can_lend(user), msg % user)
        for user in deny:
            msg = "%s can lend system"
            self.assertFalse(self.system.can_lend(user), msg % user)

    def test_can_lend(self):
        # Default state
        self.check_lending_permissions()
        # Check loan_any grants permission to lend
        lender = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_any, user=lender)
        self.check_lending_permissions(allow=[lender])
        # Check loan_self *does not* grant permission to lend
        borrower = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_self, user=borrower)
        self.check_lending_permissions(allow=[lender], deny=[borrower])
        # Check loaning the system doesn't grant permission to pass it on
        self.system.loaned = borrower
        self.check_lending_permissions(allow=[lender], deny=[borrower])

    def check_borrowing_permissions(self, allow=(), deny=()):
        self.assertTrue(self.system.can_borrow(self.owner))
        self.assertTrue(self.system.can_borrow(self.admin))
        self.assertFalse(self.system.can_borrow(self.unprivileged))
        for user in allow:
            msg = "%s cannot borrow system"
            self.assertTrue(self.system.can_borrow(user), msg % user)
        for user in deny:
            msg = "%s can borrow system"
            self.assertFalse(self.system.can_borrow(user), msg % user)

    def test_can_borrow(self):
        # Default state
        self.check_borrowing_permissions()
        # Check loan_any grants permission to borrow
        lender = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_any, user=lender)
        self.check_borrowing_permissions(allow=[lender])
        # Check loan_self grants permission to borrow
        borrower = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_self, user=borrower)
        self.check_borrowing_permissions(allow=[lender, borrower])
        # Check loan_self grants permission to update an existing loan
        self.system.loaned = borrower
        self.policy.add_rule(SystemPermission.loan_self, user=borrower)
        self.check_borrowing_permissions(allow=[lender, borrower])
        # Check ordinary users *cannot* update granted loans
        self.system.loaned = self.unprivileged
        self.check_borrowing_permissions(allow=[lender],
                                         deny=[borrower])

    def check_loan_return_permissions(self, allow=(), deny=()):
        self.assertTrue(self.system.can_return_loan(self.owner))
        self.assertTrue(self.system.can_return_loan(self.admin))
        self.assertFalse(self.system.can_return_loan(self.unprivileged))
        for user in allow:
            msg = "%s cannot return loan"
            self.assertTrue(self.system.can_return_loan(user), msg % user)
        for user in deny:
            msg = "%s can return loan"
            self.assertFalse(self.system.can_return_loan(user), msg % user)

    def test_can_return_loan(self):
        # Default state
        self.check_loan_return_permissions()
        # Check loan_any grants permission to return loans
        lender = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_any, user=lender)
        self.check_loan_return_permissions(allow=[lender])
        # Check loan_self *does not* grant permission to return loans
        borrower = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_self, user=borrower)
        self.check_loan_return_permissions(allow=[lender], deny=[borrower])
        # Check loaning the system grants permission to return it
        self.system.loaned = borrower
        self.check_loan_return_permissions(allow=[lender, borrower])
        # Check loaning it to someone else does not
        self.system.loaned = lender
        self.check_loan_return_permissions(allow=[lender], deny=[borrower])

    def check_reserve_permissions(self, allow=(), deny=()):
        # Unlike most permissions, Beaker admins can't reserve by default
        # This ensures jobs they submit don't end up running on random systems
        self.assertTrue(self.system.can_reserve(self.owner))
        self.assertFalse(self.system.can_reserve(self.admin))
        self.assertFalse(self.system.can_reserve(self.unprivileged))
        for user in allow:
            msg = "%s cannot reserve system"
            self.assertTrue(self.system.can_reserve(user), msg % user)
        for user in deny:
            msg = "%s can reserve system"
            self.assertFalse(self.system.can_reserve(user), msg % user)

    def test_can_reserve(self):
        # Default state
        self.check_reserve_permissions()
        # Check "reserve" grants permission to reserve system
        user = data_setup.create_user()
        self.policy.add_rule(SystemPermission.reserve, user=user)
        self.check_reserve_permissions(allow=[user])
        # Check "loan_any" *does not* grant permission to reserve system
        lender = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_any, user=lender)
        self.check_reserve_permissions(allow=[user], deny=[lender])
        # Check "loan_self" *does not* grant permission to reserve system
        borrower = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_self, user=borrower)
        self.check_reserve_permissions(allow=[user], deny=[lender, borrower])
        # Check loans grant the ability to reserve the system and that
        # "can_reserve" *doesn't* enforce loan exclusivity (that's handled
        # where appropriate by a separate call to is_free())
        self.system.loaned = borrower
        self.check_reserve_permissions(allow=[user, borrower], deny=[lender])
        # Check current reservations are also ignored
        self.system.user = self.unprivileged
        self.check_reserve_permissions(allow=[user, borrower], deny=[lender])

    def check_unreserve_permissions(self, allow=(), deny=()):
        self.assertTrue(self.system.can_unreserve(self.owner))
        self.assertTrue(self.system.can_unreserve(self.admin))
        self.assertFalse(self.system.can_unreserve(self.unprivileged))
        for user in allow:
            msg = "%s cannot unreserve system"
            self.assertTrue(self.system.can_unreserve(user), msg % user)
        for user in deny:
            msg = "%s can unreserve system"
            self.assertFalse(self.system.can_unreserve(user), msg % user)

    def test_can_unreserve(self):
        # Default state
        self.check_unreserve_permissions()
        # Check "loan_any" grants permission to unreserve system
        lender = data_setup.create_user()
        self.policy.add_rule(SystemPermission.loan_any, user=lender)
        self.check_unreserve_permissions(allow=[lender])
        # Check "reserve" *does not* grant permission to unreserve system
        user = data_setup.create_user()
        self.policy.add_rule(SystemPermission.reserve, user=user)
        self.check_unreserve_permissions(allow=[lender], deny=[user])
        self.system.user = lender
        self.check_unreserve_permissions(allow=[lender], deny=[user])
        # Check current user can always unreserve system
        self.system.user = user
        self.check_unreserve_permissions(allow=[lender, user])

    def test_can_power(self):
        # owner
        self.assertTrue(self.system.can_power(self.owner))
        # admin
        self.assertTrue(self.system.can_power(self.admin))
        # system's current user
        user = data_setup.create_user()
        self.assertFalse(self.system.can_power(user))
        self.system.user = user
        self.assertTrue(self.system.can_power(user))
        # granted by policy
        self.assertFalse(self.system.can_power(self.unprivileged))
        self.policy.add_rule(SystemPermission.control_system, user=self.unprivileged)
        self.assertTrue(self.system.can_power(self.unprivileged))

    def test_can_configure_netboot(self):
        # owner
        self.assertTrue(self.system.can_configure_netboot(self.owner))
        # admin
        self.assertTrue(self.system.can_configure_netboot(self.admin))
        # system's current user
        user = data_setup.create_user()
        self.assertFalse(self.system.can_configure_netboot(user))
        self.system.user = user
        self.assertTrue(self.system.can_configure_netboot(user))
        # 'control_system' permission DOES NOT grant access to configure_netboot.
        # This is mainly for historical reasons: in the past all Beaker users
        # had access to power any system, but not to "provision" it.
        self.assertFalse(self.system.can_configure_netboot(self.unprivileged))
        self.policy.add_rule(SystemPermission.control_system, user=self.unprivileged)
        self.assertFalse(self.system.can_configure_netboot(self.unprivileged))

class TestBrokenSystemDetection(DatabaseTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=637260
    # The 1-second sleeps here are so that the various timestamps
    # don't end up within the same second

    def setUp(self):
        session.begin()
        self.system = data_setup.create_system(status=SystemStatus.automated,
                lab_controller=data_setup.create_labcontroller())
        data_setup.create_completed_job(system=self.system)
        session.flush()
        time.sleep(1)

    def tearDown(self):
        session.commit()

    def abort_recipe(self, distro_tree=None, num_tasks=None, num_tasks_completed=None):
        if distro_tree is None:
            distro_tree = data_setup.create_distro_tree(distro_tags=[u'RELEASED'])
        recipe = data_setup.create_recipe(num_tasks=num_tasks, distro_tree=distro_tree)
        job = data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_installing(recipe, system=self.system)
        if num_tasks_completed is not None:
            data_setup.mark_recipe_installation_finished(recipe)
            data_setup.mark_recipe_tasks_finished(
                recipe,
                task_status=TaskStatus.completed,
                num_tasks=num_tasks_completed,
                only=True)
        recipe.abort()
        job.update_status()

    def test_multiple_suspicious_aborts_triggers_broken_system(self):
        # first aborted recipe shouldn't trigger it
        self.abort_recipe()
        self.assertNotEqual(self.system.status, SystemStatus.broken)
        # another recipe with a different stable distro *should* trigger it
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.broken)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1270649
    def test_multiple_non_suspicious_aborts_doesnt_trigger_broken_system(self):
        """This verifies that an aborted recipe is not counted as suspicious if
        some tasks completed."""
        self.abort_recipe(num_tasks=2, num_tasks_completed=1)
        self.abort_recipe(num_tasks=2, num_tasks_completed=1)
        self.assertNotEqual(self.system.status, SystemStatus.broken)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1270649
    def test_aborts_not_suspicious_if_recipe_has_completed_tasks(self):
        """This verifies that a recipe is not counted suspicious if a previous
        recipe had completed tasks."""
        self.abort_recipe()
        self.abort_recipe(num_tasks=2, num_tasks_completed=1)
        self.abort_recipe()
        self.assertNotEqual(self.system.status, SystemStatus.broken)

    def test_status_change_is_respected(self):
        # two aborted recipes should trigger it...
        self.abort_recipe()
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.broken)
        # then the owner comes along and marks it as fixed...
        self.system.status = SystemStatus.automated
        self.system.activity.append(SystemActivity(service=u'WEBUI',
                action=u'Changed', field_name=u'Status',
                old_value=u'Broken',
                new_value=unicode(self.system.status)))
        session.flush()
        time.sleep(1)
        # another recipe aborts...
        self.abort_recipe()
        self.assertNotEqual(self.system.status, SystemStatus.broken) # not broken! yet
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.broken) # now it is

    def test_counts_distinct_stable_distros(self):
        first_distro_tree = data_setup.create_distro_tree(distro_tags=[u'RELEASED'])
        # two aborted recipes for the same distro shouldn't trigger it
        self.abort_recipe(distro_tree=first_distro_tree)
        self.abort_recipe(distro_tree=first_distro_tree)
        self.assertNotEqual(self.system.status, SystemStatus.broken)
        # .. but a different distro should
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.broken)

    def test_suspicious_abort_updates_modified_date(self):
        orig_date_modified = self.system.date_modified
        self.abort_recipe()
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.broken)
        self.assert_(self.system.date_modified > orig_date_modified)

class SystemAccessPolicyTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.system = data_setup.create_system()
        self.system.custom_access_policy = SystemAccessPolicy()
        self.policy = self.system.custom_access_policy

    def tearDown(self):
        session.rollback()

    def test_add_rule_for_user(self):
        perm = SystemPermission.reserve
        user = data_setup.create_user()
        self.policy.add_rule(perm, user=user)

        self.assertEquals(len(self.policy.rules), 1)
        self.assertEquals(self.policy.rules[0].permission, perm)
        self.assertEquals(self.policy.rules[0].user, user)
        self.assert_(self.policy.rules[0].group is None)

        self.assertTrue(self.policy.grants(user, perm))
        self.assert_(SystemAccessPolicy.query
                .filter(SystemAccessPolicy.id == self.policy.id)
                .filter(SystemAccessPolicy.grants(user, perm)).count())
        other_user = data_setup.create_user()
        self.assertFalse(self.policy.grants(other_user, perm))
        self.assert_(not SystemAccessPolicy.query
                .filter(SystemAccessPolicy.id == self.policy.id)
                .filter(SystemAccessPolicy.grants(other_user, perm)).count())

    def test_add_rule_for_group(self):
        perm = SystemPermission.reserve
        group = data_setup.create_group()
        member = data_setup.create_user()
        group.add_member(member)
        self.policy.add_rule(perm, group=group)

        self.assertEquals(len(self.policy.rules), 1)
        self.assertEquals(self.policy.rules[0].permission, perm)
        self.assert_(self.policy.rules[0].user is None)
        self.assertEquals(self.policy.rules[0].group, group)

        self.assertTrue(self.policy.grants(member, perm))
        self.assert_(SystemAccessPolicy.query
                .filter(SystemAccessPolicy.id == self.policy.id)
                .filter(SystemAccessPolicy.grants(member, perm)).count())
        non_member = data_setup.create_user()
        self.assertFalse(self.policy.grants(non_member, perm))
        self.assert_(not SystemAccessPolicy.query
                .filter(SystemAccessPolicy.id == self.policy.id)
                .filter(SystemAccessPolicy.grants(non_member, perm)).count())

    def test_add_rule_for_everybody(self):
        perm = SystemPermission.reserve
        self.policy.add_rule(perm, everybody=True)

        self.assertEquals(len(self.policy.rules), 1)
        self.assertEquals(self.policy.rules[0].permission, perm)
        self.assert_(self.policy.rules[0].user is None
                and self.policy.rules[0].group is None)
        self.assertTrue(self.policy.rules[0].everybody)

        self.assertTrue(self.policy.grants_everybody(perm))
        self.assert_(SystemAccessPolicy.query
                .filter(SystemAccessPolicy.id == self.policy.id)
                .filter(SystemAccessPolicy.grants_everybody(perm)).count())
        user = data_setup.create_user()
        self.assertTrue(self.policy.grants(user, perm))
        self.assert_(SystemAccessPolicy.query
                .filter(SystemAccessPolicy.id == self.policy.id)
                .filter(SystemAccessPolicy.grants(user, perm)).count())


class SystemReleaseAction(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_power_default(self):
        system = data_setup.create_system()
        session.flush()
        self.assertEqual(system.release_action, ReleaseAction.power_off)

class CommandActivityTest(DatabaseTestCase):

    @patch('bkr.server.model.inventory.metrics')
    def test_command_completion_metrics(self, mock_metrics):
        # set up a completed command
        lc = data_setup.create_labcontroller(fqdn=u'whitehouse.gov')
        system = data_setup.create_system(lab_controller=lc, arch=u'i386')
        data_setup.configure_system_power(system, power_type=u'ilo')
        command = system.action_power(action=u'on', service=u'testdata')
        session.flush()
        command.change_status(CommandStatus.completed)
        # set up a failed command
        lc = data_setup.create_labcontroller(fqdn=u'borgen.dk')
        system = data_setup.create_system(lab_controller=lc, arch=u'x86_64')
        data_setup.configure_system_power(system, power_type=u'drac')
        command = system.action_power(action=u'off', service=u'testdata')
        session.flush()
        command.change_status(CommandStatus.failed)
        # check metrics
        counters = [
            'counters.system_commands_completed.all',
            'counters.system_commands_completed.by_lab.whitehouse_gov',
            'counters.system_commands_completed.by_arch.i386',
            'counters.system_commands_completed.by_power_type.ilo',
            'counters.system_commands_failed.all',
            'counters.system_commands_failed.by_lab.borgen_dk',
            'counters.system_commands_failed.by_arch.x86_64',
            'counters.system_commands_failed.by_power_type.drac',
        ]
        for counter in counters:
            mock_metrics.increment.assert_any_call(counter)

class TestJob(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_cc_property(self):
        job = data_setup.create_job()
        session.flush()
        session.execute(JobCc.__table__.insert(values={'job_id': job.id,
                'email_address': u'person@nowhere.example.com'}))
        session.refresh(job)
        self.assertEquals(job.cc, ['person@nowhere.example.com'])

        job.cc.append(u'korolev@nauk.su')
        session.flush()
        self.assertEquals(JobCc.query.filter_by(job_id=job.id).count(), 2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=784237
    def test_mail_exception_doesnt_prevent_status_update(self):
        job = data_setup.create_job()
        job.cc.append(u'asdf')
        data_setup.mark_job_complete(job)

    def test_stopping_completed_job_doesnt_unreserve_system(self):
        system = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller())
        admin  = data_setup.create_admin()
        job = data_setup.create_job(owner=admin)
        data_setup.mark_job_complete(job, system=system)
        # Start a new job, cancel the previously completed job
        job2 = data_setup.create_job()
        data_setup.mark_job_running(job2, system=system)
        session.flush()
        job.cancel()
        job.update_status()
        # Test that the previous cancel did not end
        # the current reservation
        self.assert_(system.open_reservation is not None)

    def test_cancel_waiting_job(self):
        job = data_setup.create_job()
        data_setup.mark_job_waiting(job)
        job.cancel()
        self.assertTrue(job.is_dirty)
        job.update_status()
        self.assertEquals(job.status, TaskStatus.cancelled)
        self.assertEquals(job.result, TaskResult.warn)

    # Check progress bar proportions are reasonable
    # https://bugzilla.redhat.com/show_bug.cgi?id=660633
    # https://bugzilla.redhat.com/show_bug.cgi?id=1014938

    # TODO: these integration tests just cover a couple of known bad cases
    # that previously rendered as 99% or 101% width. More systematic unit
    # tests would be desirable but require refactoring the progress bar
    # generation out to a data model independent helper function
    def check_progress_bar(self, bar, *expected_widths):
        # Check bar text reports 100% completion
        self.assertEqual(bar.text, "100%")
        # Check percentages are as expected
        expected_styles = ['width:%.3f%%' % width
                                 for width in expected_widths]
        styles = [elem.get('style')
                      for elem in bar.getchildren()[0].getchildren()]
        self.assertEquals(styles, expected_styles)
        widths = [float(re.match(r'width:(\d+\.\d{3})%', style).group(1))
                        for style in styles]
        # Check percentages add up to almost exactly 100%
        self.assertAlmostEqual(sum(widths), 100, delta=0.01)

    def test_progress_bar_sums_to_100_pass1_fail2(self):
        recipe = data_setup.create_recipe(
                task_list=[Task.by_name(u'/distribution/reservesys')] * 3)
        job = data_setup.create_job_for_recipes([recipe])
        recipe.tasks[0].pass_(u'/', 0, u'')
        recipe.tasks[1].fail(u'/', 0, u'')
        recipe.tasks[2].fail(u'/', 0, u'')
        data_setup.mark_job_complete(job)
        self.check_progress_bar(job.progress_bar,
                                0, 33.333, 0, 66.667, 0)

    def test_progress_bar_sums_to_100_pass4_warn1_fail1(self):
        recipe = data_setup.create_recipe(
                task_list=[Task.by_name(u'/distribution/reservesys')] * 6)
        job = data_setup.create_job_for_recipes([recipe])
        recipe.tasks[0].pass_(u'/', 0, u'')
        recipe.tasks[1].pass_(u'/', 0, u'')
        recipe.tasks[2].pass_(u'/', 0, u'')
        recipe.tasks[3].pass_(u'/', 0, u'')
        recipe.tasks[4].warn(u'/', 0, u'')
        recipe.tasks[5].fail(u'/', 0, u'')
        data_setup.mark_job_complete(job)
        self.check_progress_bar(job.progress_bar,
                                0, 66.667, 16.667, 16.667, 0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1072192
    def test_progress_bar_includes_completed_task_with_no_results(self):
        recipe = data_setup.create_recipe(
                task_list=[Task.by_name(u'/distribution/reservesys')] * 3)
        job = data_setup.create_job_for_recipes([recipe])
        recipe.tasks[0].pass_(u'/', 0, u'')
        recipe.tasks[1].pass_(u'/', 0, u'')
        # third task will be "New" due to no results recorded
        data_setup.mark_job_complete(job, result=None)
        self.assertEquals(recipe.tasks[2].result, TaskResult.new)
        self.check_progress_bar(job.progress_bar,
                                33.333, 66.667, 0, 0, 0)

    def test_create_inventory_job(self):
        lc = data_setup.create_labcontroller()
        system = data_setup.create_system(arch=[u'i386', u'x86_64'])
        system.lab_controller = lc
        distro_tree1 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                     distro_tags=[u'RELEASED'],
                                                     lab_controllers=[lc])
        session.flush()
        distro_tree = system.distro_tree_for_inventory()
        job_details = {}
        job_details['system'] = system
        job_details['whiteboard'] = 'Update Inventory for %s' % system.fqdn
        job_details['owner'] = User.by_user_name(data_setup.ADMIN_USER)
        job_xml = Job.inventory_system_job(distro_tree, **job_details)
        self.assertIn('<distroRequires>'
                      '<and>'
                      '<distro_family op="=" value="RedHatEnterpriseLinux6"/>'
                      '<distro_variant op="=" value="Server"/>'
                      '<distro_name op="=" value="%s"/>'
                      '<distro_arch op="=" value="i386"/>'
                      '</and>'
                      '</distroRequires>' % distro_tree1.distro.name,
                      job_xml)
        self.assertIn('<hostRequires force="%s"/>' % system.fqdn,
                      job_xml)
        self.assertIn('<task name="/distribution/check-install" role="STANDALONE"/>',
                      job_xml)
        self.assertIn('<task name="/distribution/inventory" role="STANDALONE"/>',
                      job_xml)

    def test_completed_n_days_ago(self):
        old_completed_job = data_setup.create_completed_job(
                finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=90))
        recently_completed_job = data_setup.create_completed_job(
                finish_time=datetime.datetime.utcnow())
        old_running_job = data_setup.create_running_job(
                queue_time=datetime.datetime.utcnow() - datetime.timedelta(days=92),
                start_time=datetime.datetime.utcnow() - datetime.timedelta(days=91))
        partially_complete_job = data_setup.create_running_job(num_recipes=2,
                queue_time=datetime.datetime.utcnow() - datetime.timedelta(days=92),
                start_time=datetime.datetime.utcnow() - datetime.timedelta(days=91))
        data_setup.mark_recipe_complete(
                partially_complete_job.recipesets[0].recipes[0], only=True,
                finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=90))

        self.assertTrue(old_completed_job.completed_n_days_ago(30))
        self.assertFalse(recently_completed_job.completed_n_days_ago(30))
        self.assertFalse(old_running_job.completed_n_days_ago(30))
        self.assertFalse(partially_complete_job.completed_n_days_ago(30))

        jobs = Job.query.filter(Job.completed_n_days_ago(30)).all()
        self.assertIn(old_completed_job, jobs)
        self.assertNotIn(recently_completed_job, jobs)
        self.assertNotIn(old_running_job, jobs)
        self.assertNotIn(partially_complete_job, jobs)

    def test_is_expired(self):
        job_already_deleted = data_setup.create_completed_job()
        job_already_deleted.deleted = datetime.datetime.utcnow()
        expired_job = data_setup.create_completed_job(retention_tag=u'60days',
                finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=61))
        unexpired_job = data_setup.create_completed_job(retention_tag=u'60days',
                finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=59))
        archived_job = data_setup.create_completed_job(retention_tag=u'audit',
                product=data_setup.create_product(),
                finish_time=datetime.datetime.utcnow() - datetime.timedelta(days=600))

        self.assertFalse(job_already_deleted.is_expired)
        self.assertTrue(expired_job.is_expired)
        self.assertFalse(unexpired_job.is_expired)
        self.assertFalse(archived_job.is_expired)

        expired_jobs = Job.query.filter(Job.is_expired).all()
        self.assertNotIn(job_already_deleted, expired_jobs)
        self.assertIn(expired_job, expired_jobs)
        self.assertNotIn(unexpired_job, expired_jobs)
        self.assertNotIn(archived_job, expired_jobs)

class DistroTreeByFilterTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_arch(self):
        excluded = data_setup.create_distro_tree(arch=u'x86_64')
        included = data_setup.create_distro_tree(arch=u'i386')
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distro_arch op="==" value="i386" />
            </distroRequires>
            """).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    def test_distro_family(self):
        excluded = data_setup.create_distro_tree(osmajor=u'PinkFootLinux4')
        included = data_setup.create_distro_tree(osmajor=u'OrangeArmLinux6')
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distro_family op="==" value="OrangeArmLinux6" />
            </distroRequires>
            """).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    def test_distro_tag_equal(self):
        excluded = data_setup.create_distro_tree(
                distro_tags=[u'INSTALLS', u'STABLE'])
        included = data_setup.create_distro_tree(
                distro_tags=[u'INSTALLS', u'STABLE', u'RELEASED'])
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distro_tag op="==" value="RELEASED" />
            </distroRequires>
            """).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    def test_distro_tag_notequal(self):
        excluded = data_setup.create_distro_tree(
                distro_tags=[u'INSTALLS', u'STABLE', u'RELEASED'])
        included = data_setup.create_distro_tree(
                distro_tags=[u'INSTALLS', u'STABLE'])
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distro_tag op="!=" value="RELEASED" />
            </distroRequires>
            """).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    def test_distro_variant(self):
        excluded = data_setup.create_distro_tree(variant=u'Server')
        included = data_setup.create_distro_tree(variant=u'ComputeNode')
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distro_variant op="==" value="ComputeNode" />
            </distroRequires>
            """).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    def test_distro_name(self):
        excluded = data_setup.create_distro_tree()
        included = data_setup.create_distro_tree()
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distro_name op="==" value="%s" />
            </distroRequires>
            """ % included.distro.name).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    def test_distrolabcontroller(self):
        excluded = data_setup.create_distro_tree()
        included = data_setup.create_distro_tree()
        lc = data_setup.create_labcontroller()
        included.lab_controller_assocs.append(LabControllerDistroTree(
                lab_controller=lc, url=u'http://notimportant'))
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distrolabcontroller op="==" value="%s" />
            </distroRequires>
            """ % lc.fqdn).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

    # https://bugzilla.redhat.com/show_bug.cgi?id=831448
    def test_distrolabcontroller_notequal(self):
        excluded = data_setup.create_distro_tree()
        included = data_setup.create_distro_tree()
        lc = data_setup.create_labcontroller()
        excluded.lab_controller_assocs.append(LabControllerDistroTree(
                lab_controller=lc, url=u'http://notimportant'))
        session.flush()
        distro_trees = DistroTree.by_filter("""
            <distroRequires>
                <distrolabcontroller op="!=" value="%s" />
            </distroRequires>
            """ % lc.fqdn).all()
        self.assert_(excluded not in distro_trees)
        self.assert_(included in distro_trees)

class WatchdogTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_not_active_watchdog_is_not_active(self):
        r1 = data_setup.create_recipe()
        r2 = data_setup.create_recipe()
        job = data_setup.create_job_for_recipes([r1, r2])
        data_setup.mark_recipe_scheduled(r1)
        data_setup.mark_recipe_running(r2)
        # r2 has a kill time hence it's "active", whereas r1 has a watchdog
        # with no kill time so it's not.
        self.assertIsNone(r1.watchdog.kill_time)
        self.assertIsNotNone(r2.watchdog.kill_time)
        session.flush()

        active_watchdogs = Watchdog.by_status()
        self.assert_(r1.watchdog not in active_watchdogs)
        self.assert_(r2.watchdog in active_watchdogs)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1123249
    def test_watchdog_is_not_expired_until_recipeset_is_expired(self):
        job = data_setup.create_running_job(num_recipes=1, num_guestrecipes=1)
        hostrecipe = job.recipesets[0].recipes[0]
        guestrecipe = job.recipesets[0].recipes[0].guests[0]
        data_setup.mark_recipe_complete(hostrecipe, only=True)
        hostrecipe.extend(0)
        self.assertLess(hostrecipe.watchdog.kill_time, datetime.datetime.utcnow())
        self.assertGreater(guestrecipe.watchdog.kill_time, datetime.datetime.utcnow())
        session.flush()
        active_watchdogs = Watchdog.by_status(status=u'active').all()
        self.assertIn(hostrecipe.watchdog, active_watchdogs)
        self.assertIn(guestrecipe.watchdog, active_watchdogs)
        expired_watchdogs = Watchdog.by_status(status=u'expired').all()
        self.assertNotIn(hostrecipe.watchdog, expired_watchdogs)
        self.assertNotIn(guestrecipe.watchdog, expired_watchdogs)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1210540
    def test_exclude_dirty_job_from_expired(self):
        recipe = data_setup.create_recipe()
        job = data_setup.create_job_for_recipes([recipe])
        data_setup.mark_job_running(job)
        recipe.extend(-1)
        session.flush()
        expired_watchdogs = Watchdog.by_status(status=u'expired').all()
        self.assertIn(recipe.watchdog, expired_watchdogs)
        job._mark_dirty()
        session.flush()
        expired_watchdogs = Watchdog.by_status(status=u'expired').all()
        self.assertNotIn(recipe.watchdog, expired_watchdogs)


class DistroTreeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.lc = data_setup.create_labcontroller()
        session.flush()

    def tearDown(self):
        session.commit()

    def test_url_in_lab(self):
        distro_tree = data_setup.create_distro_tree(arch=u'i386')
        distro_tree.lab_controller_assocs[:] = [
            LabControllerDistroTree(lab_controller=self.lc, url=u'ftp://unimportant'),
            LabControllerDistroTree(lab_controller=self.lc, url=u'nfs+iso://unimportant'),
        ]
        other_lc = data_setup.create_labcontroller()
        session.flush()

        self.assertEquals(distro_tree.url_in_lab(self.lc),
                'ftp://unimportant')
        self.assertEquals(distro_tree.url_in_lab(other_lc), None)
        self.assertRaises(ValueError, lambda:
                distro_tree.url_in_lab(other_lc, required=True))

        self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='ftp'),
                'ftp://unimportant')
        self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='http'),
                None)
        self.assertRaises(ValueError, lambda: distro_tree.url_in_lab(
                self.lc, scheme='http', required=True))

        self.assertEquals(distro_tree.url_in_lab(self.lc,
                scheme=['http', 'ftp']), 'ftp://unimportant')
        self.assertEquals(distro_tree.url_in_lab(self.lc,
                scheme=['http', 'nfs']), None)
        self.assertRaises(ValueError, lambda: distro_tree.url_in_lab(
                self.lc, scheme=['http', 'nfs'], required=True))

    def provision_distro_tree(self, distro_tree, ks_meta=None):
        recipe = data_setup.create_recipe(distro_tree=distro_tree, ks_meta=ks_meta)
        data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_waiting(recipe, lab_controller=self.lc)
        return recipe

    def test_ksmeta_ks_keyword(self):
        # Test that the 'ks_keyword' variable when put in the ks_meta attribute
        # changes the name of the value used to specify the kickstart.
        distro_rhel6 = data_setup.create_distro(osmajor=u'RedHatEnterpriseLinux6',
                                                osminor=u'5')
        rhel6_ppc64 = data_setup.create_distro_tree(distro=distro_rhel6,
                                                    arch=u'ppc64')
        r1 = self.provision_distro_tree(rhel6_ppc64, ks_meta="ks_keyword=preseed/url")
        self.assertIn('preseed/url=http://', r1.installation.kernel_options)
        self.assertNotIn('ks=', r1.installation.kernel_options)

    def test_ks_option_for_older_systems(self):
        distro_tree = data_setup.create_distro_tree(osmajor=u'CentOS7')
        recipe = self.provision_distro_tree(distro_tree)
        self.assertIn('ks=', recipe.installation.kernel_options)
        self.assertNotIn('inst.ks=', recipe.installation.kernel_options)

    def test_inst_ks_option_for_newer_systems(self):
        distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora34')
        recipe = self.provision_distro_tree(distro_tree)
        self.assertIn('inst.ks=', recipe.installation.kernel_options)
        self.assertFalse(re.search(r"(?<!inst\.)ks=", recipe.installation.kernel_options))

    def test_ksdevice_option_for_older_systems(self):
        distro_tree = data_setup.create_distro_tree(osmajor=u'CentOS7')
        recipe = self.provision_distro_tree(distro_tree)
        self.assertIn('ksdevice=bootif', recipe.installation.kernel_options)

    def test_no_ksdevice_option_for_newer_systems(self):
        distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora34')
        recipe = self.provision_distro_tree(distro_tree)
        self.assertNotIn('ksdevice', recipe.installation.kernel_options)

    def test_custom_netbootloader(self):

        # ppc64, RHEL 6
        distro_rhel6 = data_setup.create_distro(osmajor=u'RedHatEnterpriseLinux6',
                                                osminor=u'5')
        rhel6_ppc64 = data_setup.create_distro_tree(distro=distro_rhel6,
                                                    arch=u'ppc64')
        r1 = self.provision_distro_tree(rhel6_ppc64)
        self.assertIn('netbootloader=yaboot', r1.installation.kernel_options)

        # ppc64, RHEL 7.0
        distro_rhel7 = data_setup.create_distro(osmajor=u'RedHatEnterpriseLinux7',
                                                osminor=u'0')
        rhel7_ppc64 = data_setup.create_distro_tree(distro=distro_rhel7,
                                                    arch=u'ppc64')
        r2 = self.provision_distro_tree(rhel7_ppc64)
        self.assertIn('netbootloader=yaboot', r2.installation.kernel_options)

        # ppc64, RHEL 7.1
        distro_rhel71 = data_setup.create_distro(osmajor=u'RedHatEnterpriseLinux7',
                                                 osminor=u'1')
        rhel71_ppc64 = data_setup.create_distro_tree(distro=distro_rhel71,
                                                     arch=u'ppc64')
        r3 = self.provision_distro_tree(rhel71_ppc64)
        self.assertIn('netbootloader=boot/grub2/powerpc-ieee1275/core.elf',
                      r3.installation.kernel_options)

        # admin set distro option to override the default netbootloader
        distro_tree = data_setup.create_distro_tree(distro=data_setup.create_distro(),
                                                    arch=u'x86_64',
                                                    osmajor_installopts_arch= \
                                                    {'kernel_options'
                                                     :'netbootloader=something/weird'})
        r4 = self.provision_distro_tree(distro_tree)
        self.assertIn('netbootloader=something/weird', r4.installation.kernel_options)

        # ppc64, Fedora 21
        distro_f21 = data_setup.create_distro(osmajor=u'Fedora21',
                                                osminor=u'0')
        f21_ppc64 = data_setup.create_distro_tree(distro=distro_f21,
                                                    arch=u'ppc64')
        r5 = self.provision_distro_tree(f21_ppc64)
        self.assertIn('netbootloader=boot/grub2/powerpc-ieee1275/core.elf',
                      r5.installation.kernel_options)

        # ppc64, Fedora 21, custom bootloader specified as kernel option
        r6 = data_setup.create_recipe(distro_tree=f21_ppc64)
        data_setup.create_job_for_recipes([r6])
        r6.kernel_options = u'netbootloader=a/new/bootloader'
        data_setup.mark_recipe_waiting(r6)
        self.assertIn('netbootloader=a/new/bootloader',
                      r6.installation.kernel_options)

        # Manual provision
        system7 = data_setup.create_system(shared=True, lab_controller=self.lc)
        system7.provisions[f21_ppc64.arch] = Provision(arch=f21_ppc64.arch,
                                                      kernel_options='netbootloader=a/new/bootloader')
        opts = system7.manual_provision_install_options(f21_ppc64)
        self.assertEqual(opts.kernel_options['netbootloader'], 'a/new/bootloader')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1172472
    def test_leavebootorder_kernel_option_is_set_by_default_for_ppc(self):
        distro_tree = data_setup.create_distro_tree(arch=u'ppc64')
        recipe = self.provision_distro_tree(distro_tree)
        self.assertIn(u'inst.leavebootorder', recipe.installation.kernel_options.split())

    def test_leavebootorder_kernel_option_has_no_prefix_for_older_distro(self):
        distro_tree = data_setup.create_distro_tree(osmajor=u'CentOS7', arch=u'ppc64')
        recipe = self.provision_distro_tree(distro_tree)
        self.assertIn(u'leavebootorder', recipe.installation.kernel_options.split())

class OSMajorTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_arches(self):
        data_setup.create_distro_tree(osmajor=u'TestingTheArches6', arch=u'ia64')
        data_setup.create_distro_tree(osmajor=u'TestingTheArches6', arch=u'ppc64')
        session.flush()
        arches = OSMajor.by_name(u'TestingTheArches6').arches()
        self.assertEquals(set(['ia64', 'ppc64']),
                set(arch.arch for arch in arches))

    def test_install_options(self):
        o = OSMajor.lazy_create(osmajor=u'BlueShoeLinux6')
        ia64 = Arch.lazy_create(arch=u'ia64')
        OSMajorInstallOptions(osmajor=o, arch=None, ks_meta=u'one=two')
        OSMajorInstallOptions(osmajor=o, arch=ia64, kernel_options=u'serial')
        session.flush()
        self.assertEquals(set(o.install_options_by_arch.keys()),
                set([None, ia64]), o.install_options_by_arch)
        self.assertEquals(o.install_options_by_arch[None].ks_meta, u'one=two')
        self.assertEquals(o.install_options_by_arch[ia64].kernel_options,
                u'serial')

class UserTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.user = data_setup.create_user()
        session.flush()

    def tearDown(self):
        session.commit()

    def test_dictionary_password_rejected(self):
        user = data_setup.create_user()
        try:
            user.root_password = "password"
            self.fail('should raise')
        except ValueError:
            pass

    # https://bugzilla.redhat.com/show_bug.cgi?id=1121748
    def test_ldap_lookups_are_exact(self):
        # ldap-data.ldif defines 'jgillard' but ' jgillard' should not exist.
        self.assertEquals(User.by_user_name(u'jgillard').user_name, u'jgillard')
        self.assertIsNone(User.by_user_name(u' jgillard'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1121748
    def test_rfc4518_whitespace_is_rejected_in_usernames(self):
        self.assertRaises(ValueError, lambda: User(user_name=u'  leadingspace'))
        self.assertRaises(ValueError, lambda: User(user_name=u'trailingspace  '))
        self.assertRaises(ValueError, lambda: User(user_name=u'extra  space'))
        self.assertRaises(ValueError, lambda: User(user_name=u'extra\t tab'))

    def test_user_relationships(self):
        # UserActivity is a tricky one because it has two foreign keys to
        # tg_user. This is just testing that the ORM relationships are defined
        # correctly.
        user = data_setup.create_user()
        admin = data_setup.create_admin()
        user.record_activity(user=admin, service=u'testdata', field=u'Submission delegate',
                action=u'Added', new=u'asdf')
        session.flush()
        session.expire_all()
        activity = user.user_activity[0]
        self.assertIs(admin.activity[0], activity)
        self.assertEquals(activity.field_name, u'Submission delegate')
        self.assertEquals(activity.object, user)
        self.assertEquals(activity.user, admin)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_check_user_groups(self):
        user1 = data_setup.create_user()
        group = data_setup.create_group()
        group.add_member(user1)
        # create an inverted group made up of everyone
        inverted_group = data_setup.create_group(
                membership_type=GroupMembershipType.inverted)
        user2 = data_setup.create_user()
        group.add_member(user2)
        inverted_group.exclude_user(user2)
        session.flush()
        session.expire_all()
        self.assertIn(group, user1.groups)
        self.assertIn(inverted_group, user1.groups)
        self.assertIn(group, user2.groups)


class GroupTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_add_user(self):
        owner = data_setup.create_user()
        member = data_setup.create_user()
        group = data_setup.create_group(owner=owner)
        group.add_member(member)
        session.flush()

        self.assert_(group.has_owner(owner))
        self.assert_(owner in group.users)
        self.assert_(not group.has_owner(member))
        self.assert_(member in group.users)

    def check_activity(self, activity, user, service, action,
                       field, old, new):
        self.assertEquals(activity.user, user)
        self.assertEquals(activity.service, service)
        self.assertEquals(activity.action, action)
        self.assertEquals(activity.field_name, field)
        self.assertEquals(activity.old_value, old)
        self.assertEquals(activity.new_value, new)

    def test_set_name(self):
        orig_name = u'beakerdevs'
        group = Group(group_name=orig_name,
                      display_name=u'Beaker Developers')
        session.flush()
        self.assertFalse(group.is_protected_group())
        # Setting the same name is a no-op
        group.set_name(None, u'TEST', orig_name)
        self.assertEquals(len(group.activity), 0)
        # Now check changing the name is properly recorded
        new_name = u'beakerteam'
        group.set_name(None, u'TEST', new_name)
        self.assertEquals(group.group_name, new_name)
        self.assertEquals(group.display_name, u'Beaker Developers')
        self.assertEquals(len(group.activity), 1)
        self.check_activity(group.activity[0], None, u'TEST', u'Changed',
                            u'Name', orig_name, new_name)

    def test_set_display_name(self):
        orig_display_name = u'Beaker Developers'
        group = Group(group_name=u'beakerdevs',
                      display_name=orig_display_name)
        session.flush()
        # Setting the same name is a no-op
        group.set_display_name(None, u'TEST', orig_display_name)
        self.assertEquals(len(group.activity), 0)
        # Now check changing the name is properly recorded
        new_display_name = u'Beaker Team'
        group.set_display_name(None, u'TEST', new_display_name)
        self.assertEquals(group.group_name, u'beakerdevs')
        self.assertEquals(group.display_name, new_display_name)
        self.assertEquals(len(group.activity), 1)
        self.check_activity(group.activity[0], None, u'TEST', u'Changed',
                            u'Display Name',
                            orig_display_name, new_display_name)

    def test_cannot_rename_protected_groups(self):
        # The admin and lab_controller groups exist by default
        groups = [Group.by_name(u'admin')]
        groups.append(Group.by_name(u'lab_controller'))
        for group in groups:
            self.assert_(group.is_protected_group())
            orig_name = group.group_name
            orig_display_name = group.display_name
            # Can't change the real name
            self.assertRaises(BeakerException, group.set_name,
                              None, u'TEST', u'bad_rename')
            self.assertEquals(group.group_name, orig_name)
            self.assertEquals(group.display_name, orig_display_name)
            # Can change just the display name
            group.set_display_name(None, u'TEST', u'New display name')
            self.assertEquals(group.group_name, orig_name)
            self.assertEquals(group.display_name, u'New display name')


    def test_populate_ldap_group(self):
        group = Group(group_name=u'beakerdevs',
                display_name=u'Beaker Developers',
                membership_type=GroupMembershipType.ldap)
        session.add(group)
        session.flush()
        group.refresh_ldap_members()
        session.flush()
        session.expire_all()
        self.assertEquals(group.users, [User.by_user_name(u'dcallagh')])
        self.assertEquals(group.activity[0].action, u'Added')
        self.assertEquals(group.activity[0].field_name, u'User')
        self.assertEquals(group.activity[0].old_value, None)
        self.assertEquals(group.activity[0].new_value, u'dcallagh')
        self.assertEquals(group.activity[0].service, u'LDAP')

    def test_add_remove_ldap_members(self):
        # billybob will be removed, dcallagh will be added
        group = Group(group_name=u'beakerdevs',
                display_name=u'Beaker Developers',
                membership_type=GroupMembershipType.ldap)
        session.add(group)
        old_member = data_setup.create_user(user_name=u'billybob')
        group.add_member(old_member)
        session.flush()
        self.assertIn(old_member, group.users)
        group.refresh_ldap_members()
        session.flush()
        session.expire_all()
        self.assertEquals(group.users, [User.by_user_name(u'dcallagh')])
        self.assertEquals(group.activity[1].action, u'Removed')
        self.assertEquals(group.activity[1].field_name, u'User')
        self.assertEquals(group.activity[1].old_value, u'billybob')
        self.assertEquals(group.activity[1].new_value, None)
        self.assertEquals(group.activity[1].service, u'LDAP')
        self.assertEquals(group.activity[2].action, u'Added')
        self.assertEquals(group.activity[2].field_name, u'User')
        self.assertEquals(group.activity[2].old_value, None)
        self.assertEquals(group.activity[2].new_value, u'dcallagh')
        self.assertEquals(group.activity[2].service, u'LDAP')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_add_or_remove_a_normal_group_members(self):
        user = data_setup.create_user()
        user2 = data_setup.create_user()
        group = data_setup.create_group()
        group.add_member(user)
        group.add_member(user2)
        session.flush()
        session.expire_all()
        self.assertIn(user, group.users)
        self.assertIn(user2, group.users)
        group.remove_member(user2)
        session.flush()
        session.expire_all()
        self.assertNotIn(user2, group.users)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_check_group_users_in_a_normal_group(self):
        user = data_setup.create_user()
        group = data_setup.create_group()
        group.add_member(user)
        session.flush()
        session.expire_all()
        self.assertIn(user, group.users)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_check_group_users_in_an_inverted_group(self):
        group = data_setup.create_group(membership_type=GroupMembershipType.inverted)
        user = data_setup.create_user()
        user2 = data_setup.create_user()
        group.exclude_user(user2)
        session.flush()
        session.expire_all()
        self.assertIn(user, group.users)
        self.assertNotIn(user2, group.users)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_cannot_exclude_user_from_a_normal_group(self):
        group = data_setup.create_group()
        user = data_setup.create_user()
        self.assertRaises(RuntimeError, group.exclude_user,
                'Cannot exclude users from normal groups')


class TaskTypeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=816553
    def test_lazy_create_does_not_cause_duplicates(self):
        first = TaskType.lazy_create(type=u'CookieMonster')
        second = TaskType.lazy_create(type=u'CookieMonster')
        self.assert_(first is second)
        self.assertEquals(TaskType.query.filter_by(type=u'CookieMonster').count(), 1)


class RecipeSetTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.addCleanup(session.rollback)

    # https://bugzilla.redhat.com/show_bug.cgi?id=853351
    def test_comments_in_xml(self):
        job = data_setup.create_completed_job()
        recipeset = job.recipesets[0]
        commenter = data_setup.create_user(user_name=u'cpscott')
        recipeset.comments.append(RecipeSetComment(user=commenter,
                created=datetime.datetime(2015, 11, 13, 11, 54, 26),
                comment=u'is free'))
        xml = lxml.etree.tostring(recipeset.to_xml(clone=False), encoding=unicode)
        self.assertIn(u'<comments>'
                u'<comment user="cpscott" created="2015-11-13 11:54:26">'
                u'is free'
                u'</comment>'
                u'</comments>'
                u'</recipeSet>',
                xml)

class RecipeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_roles_to_xml(self):
        dt = data_setup.create_distro_tree()
        lc = data_setup.create_labcontroller()
        systems = [
            data_setup.create_system(fqdn=u'server.roles-to-xml', lab_controller=lc),
            data_setup.create_system(fqdn=u'clientone.roles-to-xml', lab_controller=lc),
            data_setup.create_system(fqdn=u'clienttwo.roles-to-xml', lab_controller=lc),
        ]
        job = data_setup.create_job_for_recipes([
            data_setup.create_recipe(distro_tree=dt, role=u'SERVER'),
            data_setup.create_recipe(distro_tree=dt, role=u'CLIENTONE'),
            data_setup.create_recipe(distro_tree=dt, role=u'CLIENTTWO'),
        ])
        for i in range(3):
            data_setup.mark_recipe_running(job.recipesets[0].recipes[i], system=systems[i])
        xml = lxml.etree.tostring(job.recipesets[0].recipes[0].to_xml(clone=False), encoding=unicode)
        self.assert_(u'<roles>'
                u'<role value="CLIENTONE"><system value="clientone.roles-to-xml"/></role>'
                u'<role value="CLIENTTWO"><system value="clienttwo.roles-to-xml"/></role>'
                u'<role value="SERVER"><system value="server.roles-to-xml"/></role>'
                u'</roles>' in xml, xml)

    def test_installation_in_xml(self):
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_complete(recipe)
        root = recipe.to_xml(clone=False)
        installation = root.find('recipeSet/recipe/installation')
        self.assertRegexpMatches(installation.get('install_started'),
                r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
        self.assertRegexpMatches(installation.get('install_finished'),
                r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
        self.assertRegexpMatches(installation.get('postinstall_finished'),
                r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')

    # https://bugzilla.redhat.com/show_bug.cgi?id=999056
    def test_empty_params_element_is_not_added_to_xml(self):
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        recipe.tasks[0].params = []
        root = recipe.to_xml(clone=True)
        task = root.find('recipeSet/recipe/task')
        self.assertEquals(len(task), 0, '<task/> should have no children')

    #https://bugzilla.redhat.com/show_bug.cgi?id=851354
    def test_hostrequires_force_clone_success(self):
        system = data_setup.create_system()
        system.status = SystemStatus.broken
        job = data_setup.create_job()

        host_requires = u'<hostRequires force="{0}"/>'
        job.recipesets[0].recipes[0]._host_requires = host_requires.format(system.fqdn)
        xml = lxml.etree.tostring(job.recipesets[0].recipes[0].to_xml(clone=True), encoding=unicode)
        self.assertIn(host_requires.format(system.fqdn), xml)

    def test_recipe_reservesys_clone(self):
        system = data_setup.create_system()
        system.status = SystemStatus.broken
        job = data_setup.create_job()
        recipe1 = data_setup.create_recipe(
            task_list=[Task.by_name(u'/distribution/check-install')] * 2,
            reservesys=True)
        recipe2 = data_setup.create_recipe(
            task_list=[Task.by_name(u'/distribution/check-install')] * 2,
            reservesys=True,
            reservesys_duration=3600)
        job = data_setup.create_job_for_recipes([recipe1, recipe2])
        xml = lxml.etree.tostring(job.recipesets[0].recipes[0].to_xml(clone=True), encoding=unicode)
        reservation_string = u'<task name="/distribution/check-install" role="STANDALONE"/>' +  \
                             u'<task name="/distribution/check-install" role="STANDALONE"/>' + \
                             u'<reservesys duration="86400" when="always"/>'
        self.assertIn(reservation_string, xml)
        xml = lxml.etree.tostring(job.recipesets[0].recipes[1].to_xml(clone=True), encoding=unicode)
        reservation_string = u'<task name="/distribution/check-install" role="STANDALONE"/>' +  \
                             u'<task name="/distribution/check-install" role="STANDALONE"/>' + \
                             u'<reservesys duration="3600" when="always"/>'
        self.assertIn(reservation_string, xml)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1122659
    def test_systemtype_is_injected_into_hostrequires(self):
        # recipe with no <hostRequires/> at all
        recipe_empty_hr = data_setup.create_recipe()
        self.assertEquals(recipe_empty_hr._host_requires, None)
        self.assertEquals(recipe_empty_hr.host_requires,
                u'<hostRequires><system_type value="Machine"/></hostRequires>')
        # recipe with <hostRequires/> but not containing <system_type/>
        recipe_other_hr = data_setup.create_recipe()
        recipe_other_hr.host_requires = u'<hostRequires><hostname value="blorp"/></hostRequires>'
        self.assertEquals(recipe_other_hr.host_requires,
                u'<hostRequires>'
                    u'<hostname value="blorp"/>'
                    u'<system_type value="Machine"/>'
                u'</hostRequires>')
        # recipe with <hostRequires/> that already contains <system_type/>
        recipe_systemtype_hr = data_setup.create_recipe()
        recipe_systemtype_hr.host_requires = (
                u'<hostRequires>'
                    u'<hostname value="blorp"/>'
                    u'<system_type value="Prototype"/>'
                u'</hostRequires>')
        self.assertEquals(recipe_systemtype_hr.host_requires,
                u'<hostRequires>'
                    u'<hostname value="blorp"/>'
                    u'<system_type value="Prototype"/>'
                u'</hostRequires>')
        # https://bugzilla.redhat.com/show_bug.cgi?id=1302950
        # recipe with <hostRequires/> that already contains <system_type/>
        # nested inside another element
        recipe_systemtype_hr = data_setup.create_recipe()
        recipe_systemtype_hr.host_requires = (
                u'<hostRequires>'
                    u'<and>'
                        u'<hostname value="blorp"/>'
                        u'<system_type value="Prototype"/>'
                    u'</and>'
                u'</hostRequires>')
        self.assertEquals(recipe_systemtype_hr.host_requires,
                u'<hostRequires>'
                    u'<and>'
                        u'<hostname value="blorp"/>'
                        u'<system_type value="Prototype"/>'
                    u'</and>'
                u'</hostRequires>')

        # Make sure system_type is not added when
        # system/type is already defined in hostRequires
        recipe_system_type = data_setup.create_recipe()
        recipe_st_host_requires = (
            u'<hostRequires>'
            u'<and>'
            u'<system>'
            u'<type op="=" value="Resource"/>'
            u'</system>'
            u'</and>'
            u'</hostRequires>'
        )
        recipe_system_type.host_requires = recipe_st_host_requires

        self.assertEquals(recipe_system_type.host_requires, recipe_st_host_requires)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1240809
    def test_get_all_logs(self):
        job = data_setup.create_completed_job(server_log=True)
        all_logs = job.recipesets[0].recipes[0].all_logs()
        self.assertEqual('http://dummy-archive-server/beaker/recipe_path/dummy.txt',
                         all_logs.next().absolute_url)
        self.assertEqual('http://dummy-archive-server/beaker/tasks/dummy.txt',
                         all_logs.next().absolute_url)
        self.assertEqual('http://dummy-archive-server/beaker/result.txt',
                         all_logs.next().absolute_url)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319
    def test_logs_appear_in_results_xml(self):
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        recipe.logs = [LogRecipe(path=u'asdf', filename='log.txt')]
        root = recipe.to_xml(clone=False)
        logs = root.findall('recipeSet/recipe/logs/log')
        self.assertEqual(logs[0].get('name'), 'asdf/log.txt')
        self.assertEqual(
                urlparse.urljoin(logs[0].base, logs[0].get('href')),
                get_server_base() + 'recipes/%s/logs/asdf/log.txt' % recipe.id)

    def test_clear_candidate_systems(self):
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        recipe.systems = [data_setup.create_system()]
        session.flush()
        recipe.clear_candidate_systems()
        self.assertEquals(recipe.systems, [])

class CheckDynamicVirtTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.user = data_setup.create_user()
        self.user.openstack_trust_id = u'dummpy_openstack_trust_id_%s' % self.user

    def tearDown(self):
        session.commit()

    def assertVirtPossible(self, recipe, msg):
        self.assertEqual(recipe.check_virtualisability(),
                         RecipeVirtStatus.possible, msg)

    def assertVirtPrecluded(self, recipe, msg):
        self.assertEqual(recipe.check_virtualisability(),
                         RecipeVirtStatus.precluded, msg)

    # Virtualisation checks added due to https://bugzilla.redhat.com/show_bug.cgi?id=902659
    def test_virt_precluded_guest_recipes(self):
        for arch in [u"i386", u"x86_64"]:
            dt = data_setup.create_distro_tree(arch=arch)
            job = data_setup.create_job(num_guestrecipes=1, distro_tree=dt,
                    owner=self.user)
            recipe = job.recipesets[0].recipes[0]
            self.assertVirtPrecluded(recipe, "Guest recipe did not preclude virt")

    def test_virt_precluded_multihost(self):
        for arch in [u"i386", u"x86_64"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe1 = data_setup.create_recipe(dt)
            recipe2 = data_setup.create_recipe(dt)
            data_setup.create_job_for_recipes([recipe1, recipe2], owner=self.user)
            self.assertVirtPrecluded(recipe1,
                                    "Multihost recipeset did not preclude virt")
            self.assertVirtPrecluded(recipe2,
                                    "Multihost recipeset did not preclude virt")

    def test_virt_precluded_host_requires(self):
        for arch in [u"i386", u"x86_64"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe = data_setup.create_recipe(dt)
            recipe.host_requires = u"""
                <hostRequires>
                    <system_type op="=" value="Prototype" />
                </hostRequires>
            """
            data_setup.create_job_for_recipes([recipe], owner=self.user)
            self.assertVirtPrecluded(recipe, "Host requires did not preclude virt")

    def test_hypervisor_hostrequires_precludes_virt(self):
        recipe = data_setup.create_recipe(arch=u'x86_64')
        recipe.host_requires = u"""
            <hostRequires>
                <hypervisor value="" />
            </hostRequires>
        """
        data_setup.create_job_for_recipes([recipe], owner=self.user)
        self.assertVirtPrecluded(recipe, "<hypervisor/> did not preclude virt")

    # Additional virt check due to https://bugzilla.redhat.com/show_bug.cgi?id=907307
    def test_virt_possible_arch(self):
        for arch in [u"i386", u"x86_64"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe = data_setup.create_recipe(dt)
            data_setup.create_job_for_recipes([recipe], owner=self.user)
            self.assertVirtPossible(recipe, "virt precluded for %s" % arch)

    def test_virt_precluded_unsupported_arch(self):
        for arch in [u"ppc", u"ppc64", u"s390", u"s390x"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe = data_setup.create_recipe(dt)
            data_setup.create_job_for_recipes([recipe], owner=self.user)
            msg = "%s did not preclude virt" % arch
            self.assertVirtPrecluded(recipe, msg)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136144
    def test_hostRequires_force_precludes_virt(self):
        recipe = data_setup.create_recipe()
        recipe.host_requires = u'<hostRequires force="somesystem.example.invalid"/>'
        data_setup.create_job_for_recipes([recipe], owner=self.user)
        self.assertVirtPrecluded(recipe, 'force="" should preclude virt')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1563072
    def test_recipe_with_invalid_custom_distro_should_not_provision(self):
        recipe = data_setup.create_recipe(custom_distro=True)
        # iPXE can only deal with HTTP or FTP URLs
        recipe.installation.tree_url = 'nfs://my.custom.distro.test/os/'
        user = data_setup.create_user()
        user.openstack_trust_id = u'dummpy_openstack_trust_id_%s' % user
        data_setup.create_job_for_recipes([recipe], owner=user)
        self.assertVirtPrecluded(recipe, 'NFS is an invalid URL')


class MachineRecipeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def _create_demo_recipes(self, arch, num_recipes, whiteboard):
        dt = data_setup.create_distro_tree(arch=arch)
        recipes = [data_setup.create_recipe(dt, whiteboard=whiteboard)
                                                for i in range(num_recipes)]
        data_setup.create_job_for_recipes(recipes)
        session.flush()
        return recipes

    def _create_recipe_with_custom_distro(self):
        recipe = data_setup.create_recipe(custom_distro=True)
        data_setup.create_job_for_recipes([recipe])
        session.flush()
        return recipe

    def _advance_recipe_states(self, recipes):
        # Advance some of the recipes through their state machine
        recipes[3].abort()
        for i in range(3):
            recipes[i].process()
        for i in range(2):
            recipes[i].queue()
        recipes[0].schedule()
        recipes[0].recipeset.job.update_status()
        return {u'new': len(recipes)-4,  u'processed': 1, u'queued': 1,
                u'scheduled': 1, u'waiting': 0, u'installing': 0,
                u'running': 0, u'reserved': 0}

    def test_get_queue_stats(self):
        expected_stats = {u'new': 0,  u'processed': 0, u'queued': 0,
                          u'scheduled': 0, u'waiting': 0, u'running': 0,
                          u'installing': 0, u'reserved': 0}
        whiteboard = u'test_get_queue_stats'
        def _get_queue_stats():
            cls = MachineRecipe
            return cls.get_queue_stats(cls.query.filter(
                                       cls.whiteboard == whiteboard))
        # Add some recipes
        recipes = self._create_demo_recipes('x86_64', 5, whiteboard)
        expected_stats[u'new'] = len(recipes)
        self.assertEqual(_get_queue_stats(), expected_stats)
        # Advance recipe states
        expected_stats = self._advance_recipe_states(recipes)
        self.assertEqual(_get_queue_stats(), expected_stats)

    def test_get_queue_stats_by_arch(self):
        expected_arches = u's390x x86_64 ppc'.split()
        default_stats = {u'new': 0,  u'processed': 0, u'queued': 0,
                         u'scheduled': 0, u'waiting': 0, u'installing': 0,
                         u'running': 0, u'reserved':0}

        expected_stats = dict((arch, default_stats.copy())
                                     for arch in expected_arches)
        whiteboard = u'test_get_queue_stats_by_arch'
        def _get_queue_stats():
            cls = MachineRecipe
            return cls.get_queue_stats_by_group(Arch.arch,
                           cls.query.filter(cls.whiteboard == whiteboard)
                                    .join(DistroTree).join(Arch))
        def _check_queue_stats(expected_stats):
            stats = _get_queue_stats()
            for arch in expected_arches:
                self.assertEqual(stats[arch], expected_stats[arch])
        # Add some recipes
        trees = []
        s390x = self._create_demo_recipes(u's390x', 2, whiteboard)
        expected_stats[u's390x'][u'new'] = len(s390x)
        ppc = self._create_demo_recipes('ppc', 3, whiteboard)
        expected_stats[u'ppc'][u'new'] = len(ppc)
        x86_64 = self._create_demo_recipes('x86_64', 5, whiteboard)
        expected_stats[u'x86_64'][u'new'] = len(x86_64)
        # Check we get the expected answers
        _check_queue_stats(expected_stats)
        # Advance x86_64 recipe states
        expected_stats[u'x86_64'] = self._advance_recipe_states(x86_64)
        # Check we get the expected answers
        _check_queue_stats(expected_stats)

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_custom_distro_xml(self):
        recipe = self._create_recipe_with_custom_distro()
        xml = recipe.to_xml()
        self.assertEqual(xml.find('recipeSet/recipe').get('distro'), 'MyAwesomeLinux1.0')
        self.assertEqual(xml.find('recipeSet/recipe').get('arch'), 'i386')
        self.assertEqual(xml.find('recipeSet/recipe').get('family'), 'DansAwesomeLinux6')
        self.assertEqual(xml.find('recipeSet/recipe').get('variant'), 'Server')
        self.assertEqual(xml.find('recipeSet/recipe/distro/tree').get('url'),
                         'ftp://dummylab.example.com/distros/MyAwesomeLinux1/')
        self.assertEqual(xml.find('recipeSet/recipe/distro/initrd').get('url'),
                         'pxeboot/initrd')
        self.assertEqual(xml.find('recipeSet/recipe/distro/kernel').get('url'),
                         'pxeboot/vmlinuz')
        self.assertEqual(xml.find('recipeSet/recipe/distro/arch').get('value'),
                         'i386')
        self.assertEqual(xml.find('recipeSet/recipe/distro/variant').get('value'),
                         'Server')
        self.assertEqual(xml.find('recipeSet/recipe/distro/name').get('value'),
                         'MyAwesomeLinux1.0')
        self.assertEqual(xml.find('recipeSet/recipe/distro/osversion').get('major'),
                         'DansAwesomeLinux6')
        self.assertEqual(xml.find('recipeSet/recipe/distro/osversion').get('minor'),
                         '0')


class GuestRecipeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_locations(self):
        lc = data_setup.create_labcontroller()
        distro_tree = data_setup.create_distro_tree(lab_controllers=[lc],
                urls=[u'nfs://something:/somewhere',
                      u'http://something/somewhere'])
        job = data_setup.create_completed_job(distro_tree=distro_tree,
                system=data_setup.create_system(lab_controller=lc),
                num_guestrecipes=1)
        guest_recipe = job.recipesets[0].recipes[0].guests[0]
        session.flush()

        guestxml = guest_recipe.to_xml()
        self.assertEqual(
                guestxml.find('recipeSet/recipe/guestrecipe').get('location'),
                u'nfs://something:/somewhere')
        self.assertEqual(
                guestxml.find('recipeSet/recipe/guestrecipe').get('nfs_location'),
                u'nfs://something:/somewhere')
        self.assertEqual(
                guestxml.find('recipeSet/recipe/guestrecipe').get('http_location'),
                u'http://something/somewhere')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1410089
    def test_location_attribute_obeys_method(self):
        lc = data_setup.create_labcontroller()
        distro_tree = data_setup.create_distro_tree(lab_controllers=[lc],
                urls=[u'nfs://something:/somewhere',
                      u'http://something/somewhere',
                      u'ftp://something/somewhere'])
        job = data_setup.create_completed_job(distro_tree=distro_tree,
                system=data_setup.create_system(lab_controller=lc),
                num_guestrecipes=1, ks_meta=u'method=ftp')
        guest_recipe = job.recipesets[0].recipes[0].guests[0]
        root = guest_recipe.to_xml(clone=False)
        expected_location = u'ftp://something/somewhere'
        location = root.find('recipeSet/recipe/guestrecipe').get('location')
        self.assertEqual(location, expected_location)
        # The point is that it must match the url command in the kickstart.
        self.assertEqual(
                guest_recipe.installation.rendered_kickstart.kickstart.splitlines()[0],
                u'url --url=%s' % expected_location)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1568238
    def test_location_for_pre_beaker_25_recipes(self):
        lc = data_setup.create_labcontroller()
        distro_tree = data_setup.create_distro_tree(lab_controllers=[lc],
                urls=[u'nfs://something:/somewhere',
                      u'http://something/somewhere',
                      u'ftp://something/somewhere'])
        job = data_setup.create_completed_job(distro_tree=distro_tree,
                lab_controller=lc, num_guestrecipes=1, ks_meta=u'method=ftp')
        guest_recipe = job.recipesets[0].recipes[0].guests[0]
        # Guest recipes prior to Beaker 25 will have a recipe.installation row
        # but missing values for the newer columns.
        guest_recipe.installation.tree_url = None
        guest_recipe.installation.initrd_path = None
        guest_recipe.installation.kernel_path = None
        guest_recipe.installation.distro_name = None
        guest_recipe.installation.osmajor = None
        guest_recipe.installation.osminor = None
        guest_recipe.installation.variant = None
        guest_recipe.installation.arch = None

        root = guest_recipe.to_xml(clone=False)
        expected_location = u'ftp://something/somewhere'
        location = root.find('recipeSet/recipe/guestrecipe').get('location')
        self.assertEqual(location, expected_location)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691666
    def test_guestname(self):
        job_1 = data_setup.create_job(num_guestrecipes=1)
        guest_recipe_1 = job_1.recipesets[0].recipes[0].guests[0]
        job_2 = data_setup.create_job(num_guestrecipes=1, guestname=u'blueguest')
        guest_recipe_2 = job_2.recipesets[0].recipes[0].guests[0]
        session.flush()

        guestxml_1 = guest_recipe_1.to_xml()
        guestxml_2 = guest_recipe_2.to_xml()
        self.assertEqual(
                guestxml_1.find('recipeSet/recipe/guestrecipe').get('guestname'),
                u'')
        self.assertEqual(
                guestxml_2.find('recipeSet/recipe/guestrecipe').get('guestname'),
                u'blueguest')

class MACAddressAllocationTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        # Other tests might have left behind running recipes using MAC
        # addresses, let's cancel them all
        running = RecipeSet.query.filter(not_(RecipeSet.status.in_(
                [s for s in TaskStatus if s.finished])))
        for rs in running:
            rs.cancel()
            rs.job.update_status()

    def tearDown(self):
        session.rollback()

    def test_lowest_free_mac_none_in_use(self):
        self.assertEquals(RecipeResource._lowest_free_mac(),
                netaddr.EUI('52:54:00:00:00:00'))

    def test_lowest_free_mac_one_in_use(self):
        job = data_setup.create_job(num_guestrecipes=1)
        data_setup.mark_job_running(job)
        self.assertEquals(job.recipesets[0].recipes[0].guests[0].resource.mac_address,
                    netaddr.EUI('52:54:00:00:00:00'))
        self.assertEquals(RecipeResource._lowest_free_mac(),
                    netaddr.EUI('52:54:00:00:00:01'))

    def test_lowest_free_mac_gap_at_start(self):
        first_job = data_setup.create_job(num_guestrecipes=1)
        data_setup.mark_job_running(first_job)
        self.assertEquals(first_job.recipesets[0].recipes[0].guests[0].resource.mac_address,
                    netaddr.EUI('52:54:00:00:00:00'))
        second_job = data_setup.create_job(num_guestrecipes=1)
        data_setup.mark_job_running(second_job)
        self.assertEquals(second_job.recipesets[0].recipes[0].guests[0].resource.mac_address,
                    netaddr.EUI('52:54:00:00:00:01'))
        self.assertEquals(RecipeResource._lowest_free_mac(),
                    netaddr.EUI('52:54:00:00:00:02'))
        first_job.cancel()
        first_job.update_status()
        self.assertEquals(RecipeResource._lowest_free_mac(),
                    netaddr.EUI('52:54:00:00:00:00'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=903893#c12
    def test_guestrecipe_complete_but_recipeset_incomplete(self):
        job = data_setup.create_job(num_guestrecipes=1)
        data_setup.mark_job_running(job)
        self.assertEquals(job.recipesets[0].recipes[0].guests[0].resource.mac_address,
                    netaddr.EUI('52:54:00:00:00:00'))
        data_setup.mark_recipe_complete(job.recipesets[0].recipes[0].guests[0], only=True)
        # host recipe may still be running reservesys or some other task,
        # even after the guest recipe is finished...
        self.assertEquals(job.recipesets[0].recipes[0].status, TaskStatus.running)
        self.assertEquals(job.recipesets[0].status, TaskStatus.running)
        # ... so we mustn't re-use the MAC address yet
        self.assertEquals(RecipeResource._lowest_free_mac(),
                    netaddr.EUI('52:54:00:00:00:01'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=912159
    def test_in_use_below_base_address(self):
        job = data_setup.create_job(num_guestrecipes=1)
        data_setup.mark_job_running(job)
        # This can happen if the base address was previously set to a lower
        # value, and a guest recipe from then is still running.
        job.recipesets[0].recipes[0].guests[0].resource.mac_address = \
            netaddr.EUI('52:53:FF:00:00:00')
        self.assertEquals(RecipeResource._lowest_free_mac(),
                netaddr.EUI('52:54:00:00:00:00'))
        job.cancel()
        job.update_status()
        self.assertEquals(RecipeResource._lowest_free_mac(),
                netaddr.EUI('52:54:00:00:00:00'))

class VirtResourceTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.addCleanup(session.rollback)

    def test_link(self):
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_installing(recipe, virt=True)
        # when recipe first starts we don't have an fqdn
        expected_hyperlink = ('<a href="http://openstack.example.invalid/'
                'dashboard/project/instances/{0}/">{0}</a>'
                .format(recipe.resource.instance_id))
        self.assertEquals(serialize_kid_element(recipe.resource.link),
                '<span>(OpenStack instance {0})</span>'.format(expected_hyperlink))
        # when installation finishes, we have an fqdn
        data_setup.mark_recipe_installation_finished(recipe,
                fqdn=u'my-openstack-instance')
        self.assertEquals(serialize_kid_element(recipe.resource.link),
                '<span>my-openstack-instance (OpenStack instance {0})</span>'
                .format(expected_hyperlink))
        # after the recipe completes, we don't link to the deleted instance
        data_setup.mark_recipe_complete(recipe, only=True)
        self.assertEquals(serialize_kid_element(recipe.resource.link),
                '<span>my-openstack-instance (OpenStack instance {0})</span>'
                .format(recipe.resource.instance_id))

class LogRecipeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.recipe = data_setup.create_recipe()
        self.recipe.logs[:] = []
        data_setup.create_job_for_recipes([self.recipe])

    def tearDown(self):
        session.rollback()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1014875
    def test_lazy_create_can_deal_with_deadlocks(self):
        global _raise_counter
        _max_valid_attempts = 6
        orig_ConditionalInsert = model.base.ConditionalInsert
        def _raise_deadlock_exception(raise_this_many=0):

            global _raise_counter
            _raise_counter = 0
            def inner(*args, **kwargs):
                global _raise_counter
                if _raise_counter < raise_this_many:
                    _raise_counter += 1
                    raise OperationalError('statement', {}, '(OperationalError) (1213, blahlbha')
                model.base.ConditionalInsert = orig_ConditionalInsert
                return model.base.ConditionalInsert(*args, **kwargs)

            return inner

        try:
            # This should raise 3 times and then just work
            model.base.ConditionalInsert = _raise_deadlock_exception(3)
            lr1 = LogRecipe.lazy_create(path=u'/', filename=u'dummy.log',
                    recipe_id=self.recipe.id)
            self.assertEquals(_raise_counter, 3)
            self.assertTrue(lr1.id)

            # We should have no deadlock exception now
            _raise_counter = 0
            model.base.ConditionalInsert = _raise_deadlock_exception(0)
            lr2 = LogRecipe.lazy_create(path=u'/', filename=u'dummy2.log',
                    recipe_id=self.recipe.id)
            self.assertEquals(_raise_counter, 0)
            self.assertTrue(lr2.id)

            # We should exhaust our max number of attempts.
            _raise_counter = 0
            model.base.ConditionalInsert = _raise_deadlock_exception(_max_valid_attempts + 1)
            try:
                LogRecipe.lazy_create(path=u'/', filename=u'dummy3.log',
                        recipe_id=self.recipe.id)
                self.fail('We should only allow %s attempts' % _max_valid_attempts)
            except OperationalError, e:
                if '(OperationalError) (1213, blahlbha' not in unicode(e):
                    raise
            self.assertEquals(_raise_counter, _max_valid_attempts)
        finally:
            model.base.ConditionalInsert = orig_ConditionalInsert

    # https://bugzilla.redhat.com/show_bug.cgi?id=865265
    def test_path_is_normalized(self):
        lr1 = LogRecipe.lazy_create(path=u'/', filename=u'dummy.log',
                recipe_id=self.recipe.id)
        lr2 = LogRecipe.lazy_create(path=u'', filename=u'dummy.log',
                recipe_id=self.recipe.id)
        self.assert_(lr1 is lr2, (lr1, lr2))


class TaskPackageTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=816553
    def test_lazy_create_does_not_cause_duplicates(self):
        first = TaskPackage.lazy_create(package=u'beaker')
        second = TaskPackage.lazy_create(package=u'beaker')
        self.assert_(first is second)
        self.assertEquals(TaskPackage.query.filter_by(package=u'beaker').count(), 1)

class DeviceClassTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=816553
    def test_lazy_create_does_not_cause_duplicates(self):
        first = DeviceClass.lazy_create(device_class=u'washing_machine')
        second = DeviceClass.lazy_create(device_class=u'washing_machine')
        self.assert_(first is second)
        self.assertEquals(DeviceClass.query.filter_by(device_class=u'washing_machine').count(), 1)

class DeviceTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    # https://bugzilla.redhat.com/show_bug.cgi?id=816553
    def test_lazy_create_does_not_cause_duplicates(self):
        device_class = DeviceClass.lazy_create(device_class=u'NETWORK')
        params = dict(device_class_id=device_class.id,
                vendor_id=u'8086', device_id=u'1111',
                subsys_vendor_id=u'8086', subsys_device_id=u'1111',
                bus=u'pci', driver=u'e1000',
                description=u'lol')
        first = Device.lazy_create(**params)
        second = Device.lazy_create(**params)
        self.assert_(first is second)
        self.assertEquals(Device.query.filter_by(**params).count(), 1)

class TaskTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.close()

    def test_schema_in_task_details_xml_output(self):
        schema_doc = lxml.etree.parse(pkg_resources.resource_stream(
                        'bkr.common', 'schema/beaker-task.rng'))
        schema = lxml.etree.RelaxNG(schema_doc)

        vals = [None, True, False]

        for destructive, nda in [(_, __) for _ in vals for __ in vals]:
            task = data_setup.create_task()
            task.destructive = destructive
            task.nda = nda
            session.flush()

            doc = lxml.etree.fromstring(task.to_xml())
            self.assert_(schema.validate(doc) is True)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915549
    def test_duplicate_task(self):

        task = data_setup.create_task(name=u'Task1')
        session.flush()
        with self.assertRaises(IntegrityError):
            data_setup.create_task(name=u'Task1')
            session.flush()

    def test_compatible_with_osmajor_obeys_excluded_releases(self):
        rhel6 = OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinux6')
        incompatible_task = data_setup.create_task(exclude_osmajors=[u'RedHatEnterpriseLinux6'])
        compatible_task = data_setup.create_task(exclude_osmajors=[
                u'RedHatEnterpriseLinuxServer5', u'RedHatEnterpriseLinuxClient5'])
        session.flush()
        filtered = Task.query.filter(Task.compatible_with_osmajor(rhel6)).all()
        self.assertNotIn(incompatible_task, filtered)
        self.assertIn(compatible_task, filtered)

    # https://bugzilla.redhat.com/show_bug.cgi?id=800455
    def test_compatible_with_osmajor_obeys_exclusive_releases(self):
        rhel6 = OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinux6')
        compatible_task = data_setup.create_task(exclusive_osmajors=[u'RedHatEnterpriseLinux6'])
        incompatible_task = data_setup.create_task(exclusive_osmajors=[
                u'RedHatEnterpriseLinuxServer5', u'RedHatEnterpriseLinuxClient5'])
        session.flush()
        filtered = Task.query.filter(Task.compatible_with_osmajor(rhel6)).all()
        self.assertIn(compatible_task, filtered)
        self.assertNotIn(incompatible_task, filtered)

class TaskLibraryTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.task_rpm_name_new = 'tmp-distribution-beaker-task_test-2.1-0.noarch.rpm'
        self.task_rpm_name_old = 'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'
        self.task_rpm_new = pkg_resources.resource_filename('bkr.inttest.server',
                                                            'task-rpms/' + self.task_rpm_name_new)
        self.task_rpm_old = pkg_resources.resource_filename('bkr.inttest.server',
                                                            'task-rpms/' + self.task_rpm_name_old)

    def tearDown(self):
        session.rollback()

    def query_task_repo(self, task_name):

        task_dir = turbogears.config.get('basepath.rpms')
        base = dnf.Base()
        cachedir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cachedir)
        base.conf.cachedir = cachedir
        base.repos.add_new_repo('myrepo', base.conf, baseurl=['file://' + os.path.abspath(task_dir)])
        base.fill_sack(load_system_repo=False)
        packages = base.sack.query().filter(name=task_name).run()
        return [''.join([pkg.version, '-', pkg.release]) for pkg in packages]

    def write_data_file(self, rpm):
        rpm_data = open(rpm)

        def write_data(f):
            f.write(rpm_data.read())
        return write_data

    #https://bugzilla.redhat.com/show_bug.cgi?id=1044934
    def test_downgrade_task(self):

        # first add a "newer" task
        Task.update_task(self.task_rpm_name_new,
                         self.write_data_file(self.task_rpm_new))
        # Downgrade now
        Task.update_task(self.task_rpm_name_old,
                         self.write_data_file(self.task_rpm_old))

        # query the task repo and check the version and release
        results = self.query_task_repo('tmp-distribution-beaker-task_test')
        self.assertEquals(len(results), 1)
        self.assertEquals(results[0], '1.1-0')

    def test_upgrade_task(self):

        Task.update_task(self.task_rpm_name_old,
                         self.write_data_file(self.task_rpm_old))
        Task.update_task(self.task_rpm_name_new,
                         self.write_data_file(self.task_rpm_new))

        # query the task repo and check the version and release
        vr_list = self.query_task_repo('tmp-distribution-beaker-task_test')
        self.assertEquals(len(vr_list), 2)
        self.assertIn('1.1-0', vr_list)
        self.assertIn('2.1-0', vr_list)

class RecipeTaskTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        recipe = data_setup.create_recipe(task_name=u'/distribution/check-install')
        data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_running(recipe)
        self.recipetask = recipe.tasks[0]

    def tearDown(self):
        session.rollback()

    def test_version_in_xml(self):
        self.recipetask.version = u'1.2-3'
        root = self.recipetask.to_xml(clone=False)
        self.assertEquals(root.get('version'), u'1.2-3')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1303023
    def test_results_in_xml(self):
        self.recipetask.pass_(u'/start', 0, u'Install Started')
        self.recipetask.fail(u'/', 0, u'(Fail)')
        root = self.recipetask.to_xml(clone=False)
        results = root.find('results').findall('result')
        self.assertEqual(results[0].get('path'), u'/start')
        self.assertEqual(results[0].get('score'), u'0')
        self.assertEqual(results[0].get('result'), u'Pass')
        self.assertEqual(results[0].text, u'Install Started')
        self.assertEqual(results[1].get('path'), u'/')
        self.assertEqual(results[1].get('score'), u'0')
        self.assertEqual(results[1].get('result'), u'Fail')
        self.assertEqual(results[1].text, u'(Fail)')

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319
    def test_logs_appear_in_results_xml(self):
        self.recipetask.logs.append(LogRecipeTask(path=u'asdf', filename=u'log.txt'))
        root = self.recipetask.to_xml(clone=False)
        logs = root.find('logs').findall('log')
        self.assertEqual(logs[0].get('name'), 'asdf/log.txt')
        self.assertEqual(
                urlparse.urljoin(logs[0].base, logs[0].get('href')),
                get_server_base() + 'recipes/%s/tasks/%s/logs/asdf/log.txt'
                    % (self.recipetask.recipe.id, self.recipetask.id))

class RecipeTaskResultTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.job = data_setup.create_running_job()
        self.recipe = self.job.recipesets[0].recipes[0]
        self.recipe_task = self.recipe.tasks[0]

    def tearDown(self):
        session.rollback()

    def test_display_label(self):
        task = Task.by_name(u'/distribution/check-install')
        rt = RecipeTask.from_task(task)
        rtr = RecipeTaskResult(recipetask=rt, path=u'/distribution/check-install/Sysinfo')
        self.assertEquals(rtr.display_label, u'Sysinfo')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/start')
        self.assertEquals(rtr.display_label, u'/start')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/distribution/check-install')
        self.assertEquals(rtr.display_label, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/distribution/check-install/')
        self.assertEquals(rtr.display_label, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=None)
        self.assertEquals(rtr.display_label, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=u'')
        self.assertEquals(rtr.display_label, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/')
        self.assertEquals(rtr.display_label, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=None, log='Cancelled it')
        self.assertEquals(rtr.display_label, u'Cancelled it')
        rtr = RecipeTaskResult(recipetask=rt, path=u'', log='Cancelled it')
        self.assertEquals(rtr.display_label, u'Cancelled it')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/', log='Cancelled it')
        self.assertEquals(rtr.display_label, u'Cancelled it')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1586049
    def test_coerces_string_for_score(self):
        task = Task.by_name(u'/distribution/check-install')
        rt = RecipeTask.from_task(task)
        rt.recipe_id = self.recipe.id
        rt._result(TaskResult.pass_, path='.', score='', summary='empty string')
        rt._result(TaskResult.pass_, path='.', score='123foo', summary='numbered string')
        rt._result(TaskResult.pass_, path='.', score='/foo/bar', summary='path')
        rt._result(TaskResult.pass_, path='.', score='8.88', summary='truncated')
        rt._result(TaskResult.pass_, path='.', score='8.8.8', summary='invalid decimal')
        rt._result(TaskResult.pass_, path='.', score='-1', summary='negative')
        rt._result(TaskResult.pass_, path='.', score='10', summary='correct')
        session.flush()

        session.refresh(rt)
        expected = [(u'empty string', Decimal(0)),
                    (u'numbered string', Decimal(123)),
                    (u'path', Decimal(0)),
                    (u'truncated', Decimal(9)),
                    (u'invalid decimal', Decimal(9)),
                    (u'negative', Decimal(-1)),
                    (u'correct', Decimal(10)),
        ]
        self.assertEquals(expected, [(x.log, x.score) for x in rt.results])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1600281
    def test_caps_very_large_score(self):
        self.recipe_task.pass_(path=u'/distribution/kernelinstall/Sysinfo', score='12345678900', summary=None)
        session.refresh(self.recipe_task)
        self.assertEquals(self.recipe_task.results[0].score, 9999999999)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319
    def test_logs_appear_in_results_xml(self):
        rtr_id = self.recipe_task.pass_(path=u'.', score=None, summary=None)
        rtr = RecipeTaskResult.query.get(rtr_id)
        rtr.logs = [LogRecipeTaskResult(path=u'asdf', filename=u'log.txt')]
        root = rtr.to_xml(clone=False)
        logs = root.find('logs').findall('log')
        self.assertEqual(logs[0].get('name'), 'asdf/log.txt')
        self.assertEqual(
                urlparse.urljoin(logs[0].base, logs[0].get('href')),
                get_server_base() + 'recipes/%s/tasks/%s/results/%s/logs/asdf/log.txt'
                    % (self.recipe.id, self.recipe_task.id, rtr.id))


class TestSystemInventoryDistro(DatabaseTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.system1 = data_setup.create_system(arch=[u'i386', u'x86_64'])
            self.system1.lab_controller = self.lc
            self.system2 = data_setup.create_system(arch=[u'i386'])
            self.system2.lab_controller = self.lc
            self.system3 = data_setup.create_system(arch=[u'ppc64', u'ppc64le'])
            self.system3.lab_controller = self.lc
            self.system4 = data_setup.create_system(arch=[u'ppc64le'])
            self.system4.lab_controller = self.lc
            self.system5 = data_setup.create_system(arch=[u's390', u's390x'])
            self.system5.lab_controller = self.lc
            self.system6 = data_setup.create_system(arch=[u's390'])
            self.system6.lab_controller = self.lc
            self.system7 = data_setup.create_system(arch=[u'aarch64'])
            self.system7.lab_controller = self.lc
            self.distro_tree1 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
            self.distro_tree2 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              arch=u'x86_64',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
            self.distro_tree3 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux7',
                                                              arch=u'ppc64',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
            self.distro_tree4 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux7',
                                                              arch=u'ppc64le',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
            self.distro_tree5 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              arch=u's390x',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
            self.distro_tree6 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              arch=u's390',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
            self.distro_tree7 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux7',
                                                              arch=u'aarch64',
                                                              lab_controllers=[self.lc])

            # setup a system in a different LC with only a Fedora distro
            self.lc1 = data_setup.create_labcontroller()
            self.system8 = data_setup.create_system(arch=[u'i386', u'x86_64'])
            self.system8.lab_controller = self.lc1
            self.distro_tree8 = data_setup.create_distro_tree(osmajor=u'Fedora22',
                                                              arch=u'i386',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc1])
            # setup a system in a different LC with a unknown distro
            self.lc2 = data_setup.create_labcontroller()
            self.system9 = data_setup.create_system(arch=[u'i386', u'x86_64'])
            self.system9.lab_controller = self.lc2
            self.distro_tree9 = data_setup.create_distro_tree(osmajor=u'MyDistro',
                                                              arch=u'x86_64',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc2])

    def test_select_inventory_distro_tree_released(self):
        # For system1, x86_64 tree should be preferred
        with session.begin():
            self.assertEquals(self.system1.distro_tree_for_inventory(), self.distro_tree2)
        # For system2, i386 tree should be chosen
        with session.begin():
            self.assertEquals(self.system2.distro_tree_for_inventory(), self.distro_tree1)

        # For system3, ppc64 tree should be preferred
        with session.begin():
            self.assertEquals(self.system3.distro_tree_for_inventory(), self.distro_tree3)
        # For system4, ppc64le tree should be chosen
        with session.begin():
            self.assertEquals(self.system4.distro_tree_for_inventory(), self.distro_tree4)

        # For system5, s390x tree should be preferred
        with session.begin():
            self.assertEquals(self.system5.distro_tree_for_inventory(), self.distro_tree5)
        # For system6, s390 tree should be chosen
        with session.begin():
            self.assertEquals(self.system6.distro_tree_for_inventory(), self.distro_tree6)

        # For system8, the Fedora22 tree should be found
        # tests that we keep looking for the recognized distros till
        # we find one.
        with session.begin():
            self.assertEquals(self.system8.distro_tree_for_inventory(), self.distro_tree8)

    def test_distro_tree_for_inventory_no_released_tree(self):
        with session.begin():
            self.assertEquals(self.system7.distro_tree_for_inventory(), self.distro_tree7)

    def test_distro_tree_for_inventory_no_preferred_tree(self):
        with session.begin():
            self.assertEquals(self.system9.distro_tree_for_inventory(), self.distro_tree9)


class TestLabController(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_invalid_fqdn(self):
        lc = data_setup.create_labcontroller()
        try:
            lc.fqdn = ''
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('Lab controller FQDN must not be empty', str(e))
        try:
            lc.fqdn = 'invalid_lc_fqdn'
            self.fail('Must fail or die')
        except ValueError as e:
            self.assertIn('Invalid FQDN for lab controller', str(e))

if __name__ == '__main__':
    unittest.main()
