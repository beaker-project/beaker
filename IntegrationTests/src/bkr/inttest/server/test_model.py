
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import re
import time
import datetime
import unittest2 as unittest
import pkg_resources
import shutil
import lxml.etree
import email
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
        RecipeReservationRequest, ReleaseAction
from bkr.server.bexceptions import BeakerException
from sqlalchemy.sql import not_
from sqlalchemy.exc import OperationalError
import netaddr
from bkr.inttest import data_setup, DatabaseTestCase
from nose.plugins.skip import SkipTest
import turbogears
import os
import yum

def serialize_kid_element(elem):
    return kid.XHTMLSerializer().serialize(kid.ElementStream(elem), fragment=True)

class SchemaSanityTest(DatabaseTestCase):

    def test_all_tables_use_innodb(self):
        engine = DeclarativeMappedObject.metadata.bind
        if engine.url.drivername != 'mysql':
            raise SkipTest('not using MySQL')
        for table in engine.table_names():
            self.assertEquals(engine.scalar(
                    'SELECT engine FROM information_schema.tables '
                    'WHERE table_schema = DATABASE() AND table_name = %s',
                    table), 'InnoDB')

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
        self.assertEqual(ActivityMixin._fields, params)

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
                     serial=None))

    def test_mark_broken_updates_history(self):
        system = data_setup.create_system(status = SystemStatus.automated)
        system.mark_broken(reason = "Attacked by cyborgs")
        session.flush()
        system_activity = system.dyn_activity.filter(SystemActivity.field_name == u'Status').first()
        self.assertEqual(system_activity.old_value, u'Automated')
        self.assertEqual(system_activity.new_value, u'Broken')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1020153
    def test_markdown_rendering_errors_ignored(self):
        # Set up system and expected note output
        system = data_setup.create_system()
        note_text = "<this will break python-markdown in RHEL 6.4>"
        system.add_note(note_text, system.owner)
        # Ensure the markdown call fails
        def bad_markdown(data, *args, **kwds):
            self.assertEqual(data, note_text)
            raise Exception("HTML converter should have stopped this...")
        orig_markdown = model.inventory.markdown
        model.inventory.markdown = bad_markdown
        try:
            actual = system.notes[0].html
        finally:
            model.inventory.markdown = orig_markdown
        self.assertEqual(actual, note_text)

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
                lambda s: s.compatible_with_distro_tree(distro_tree),
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

    def abort_recipe(self, distro_tree=None):
        if distro_tree is None:
            distro_tree = data_setup.create_distro_tree(distro_tags=[u'RELEASED'])
        recipe = data_setup.create_recipe(distro_tree=distro_tree)
        job = data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_running(recipe, system=self.system)
        recipe.abort()
        job.update_status()

    def test_multiple_suspicious_aborts_triggers_broken_system(self):
        # first aborted recipe shouldn't trigger it
        self.abort_recipe()
        self.assertNotEqual(self.system.status, SystemStatus.broken)
        # another recipe with a different stable distro *should* trigger it
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.broken)

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

    def test_updates_modified_date(self):
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
        member.groups.append(group)
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
        self.assertNotEquals(job.dirty_version, job.clean_version)
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
        job.update_status()
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
        job.update_status()
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
        job.update_status()
        self.check_progress_bar(job.progress_bar,
                                33.333, 66.667, 0, 0, 0)


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
        lc = data_setup.create_labcontroller(
                fqdn=u'DistroTreeByFilterTest.test_distrolabcontroller')
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
        data_setup.mark_recipe_waiting(r1)
        data_setup.mark_recipe_running(r2)
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


class DistroTreeTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.distro_tree = data_setup.create_distro_tree(arch=u'i386')
        self.lc = data_setup.create_labcontroller()
        session.flush()

    def tearDown(self):
        session.commit()

    def test_url_in_lab(self):
        self.distro_tree.lab_controller_assocs[:] = [
            LabControllerDistroTree(lab_controller=self.lc, url=u'ftp://unimportant'),
            LabControllerDistroTree(lab_controller=self.lc, url=u'nfs+iso://unimportant'),
        ]
        other_lc = data_setup.create_labcontroller()
        session.flush()

        self.assertEquals(self.distro_tree.url_in_lab(self.lc),
                'ftp://unimportant')
        self.assertEquals(self.distro_tree.url_in_lab(other_lc), None)
        self.assertRaises(ValueError, lambda:
                self.distro_tree.url_in_lab(other_lc, required=True))

        self.assertEquals(self.distro_tree.url_in_lab(self.lc, scheme='ftp'),
                'ftp://unimportant')
        self.assertEquals(self.distro_tree.url_in_lab(self.lc, scheme='http'),
                None)
        self.assertRaises(ValueError, lambda: self.distro_tree.url_in_lab(
                self.lc, scheme='http', required=True))

        self.assertEquals(self.distro_tree.url_in_lab(self.lc,
                scheme=['http', 'ftp']), 'ftp://unimportant')
        self.assertEquals(self.distro_tree.url_in_lab(self.lc,
                scheme=['http', 'nfs']), None)
        self.assertRaises(ValueError, lambda: self.distro_tree.url_in_lab(
                self.lc, scheme=['http', 'nfs'], required=True))

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

class GroupTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_add_user(self):
        owner = data_setup.create_user()
        member = data_setup.create_user()
        group = data_setup.create_group(owner=owner)
        group.users.append(member)
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
        # As is setting None
        group.set_name(None, u'TEST', None)
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
        # As is setting None
        group.set_display_name(None, u'TEST', None)
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
        # The queue_admin group is also special, but not created by default
        groups.append(data_setup.create_group(group_name=u'queue_admin'))
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
                display_name=u'Beaker Developers', ldap=True)
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
                display_name=u'Beaker Developers', ldap=True)
        old_member = data_setup.create_user(user_name=u'billybob')
        group.users.append(old_member)
        self.assertEquals(group.users, [old_member])
        session.flush()
        group.refresh_ldap_members()
        session.flush()
        session.expire_all()
        self.assertEquals(group.users, [User.by_user_name(u'dcallagh')])
        self.assertEquals(group.activity[0].action, u'Removed')
        self.assertEquals(group.activity[0].field_name, u'User')
        self.assertEquals(group.activity[0].old_value, u'billybob')
        self.assertEquals(group.activity[0].new_value, None)
        self.assertEquals(group.activity[0].service, u'LDAP')
        self.assertEquals(group.activity[1].action, u'Added')
        self.assertEquals(group.activity[1].field_name, u'User')
        self.assertEquals(group.activity[1].old_value, None)
        self.assertEquals(group.activity[1].new_value, u'dcallagh')
        self.assertEquals(group.activity[1].service, u'LDAP')


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
        xml = job.recipesets[0].recipes[0].to_xml(clone=False).toxml()
        self.assert_('<roles>'
                '<role value="CLIENTONE"><system value="clientone.roles-to-xml"/></role>'
                '<role value="CLIENTTWO"><system value="clienttwo.roles-to-xml"/></role>'
                '<role value="SERVER"><system value="server.roles-to-xml"/></role>'
                '</roles>' in xml, xml)

    def test_installation_in_xml(self):
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_complete(recipe)
        root = lxml.etree.fromstring(recipe.to_xml(clone=False).toxml())
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
        root = lxml.etree.fromstring(recipe.to_xml(clone=True).toxml())
        task = root.find('recipeSet/recipe/task')
        self.assertEquals(len(task), 0, '<task/> should have no children')

    #https://bugzilla.redhat.com/show_bug.cgi?id=851354
    def test_hostrequires_force_clone_success(self):
        system = data_setup.create_system()
        system.status = SystemStatus.broken
        job = data_setup.create_job()

        host_requires = '<hostRequires force="{0}"/>'
        job.recipesets[0].recipes[0]._host_requires = host_requires.format(system.fqdn)
        xml = job.recipesets[0].recipes[0].to_xml(clone=True).toxml()
        self.assertIn(host_requires.format(system.fqdn), xml)

    def test_recipe_reservesys_clone(self):
        system = data_setup.create_system()
        system.status = SystemStatus.broken
        job = data_setup.create_job()
        recipe1 = data_setup.create_recipe(
            task_list=[Task.by_name(u'/distribution/install')] * 2,
            reservesys=True)
        recipe2 = data_setup.create_recipe(
            task_list=[Task.by_name(u'/distribution/install')] * 2,
            reservesys=True,
            reservesys_duration=3600)
        job = data_setup.create_job_for_recipes([recipe1, recipe2])
        xml = job.recipesets[0].recipes[0].to_xml(clone=True).toxml()
        reservation_string = '<task name="/distribution/install" role="STANDALONE"/>' +  \
                             '<task name="/distribution/install" role="STANDALONE"/>' + \
                             '<reservesys duration="86400"/>'
        self.assertIn(reservation_string, xml)
        xml = job.recipesets[0].recipes[1].to_xml(clone=True).toxml()
        reservation_string = '<task name="/distribution/install" role="STANDALONE"/>' +  \
                             '<task name="/distribution/install" role="STANDALONE"/>' + \
                             '<reservesys duration="3600"/>'
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

class CheckDynamicVirtTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

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
            job = data_setup.create_job(num_guestrecipes=1, distro_tree=dt)
            recipe = job.recipesets[0].recipes[0]
            self.assertVirtPrecluded(recipe, "Guest recipe did not preclude virt")

    def test_virt_precluded_multihost(self):
        for arch in [u"i386", u"x86_64"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe1 = data_setup.create_recipe(dt)
            recipe2 = data_setup.create_recipe(dt)
            data_setup.create_job_for_recipes([recipe1, recipe2])
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
            data_setup.create_job_for_recipes([recipe])
            self.assertVirtPrecluded(recipe, "Host requires did not preclude virt")

    def test_hypervisor_hostrequires_precludes_virt(self):
        recipe = data_setup.create_recipe(arch=u'x86_64')
        recipe.host_requires = u"""
            <hostRequires>
                <hypervisor value="" />
            </hostRequires>
        """
        data_setup.create_job_for_recipes([recipe])
        self.assertVirtPrecluded(recipe, "<hypervisor/> did not preclude virt")

    # Additional virt check due to https://bugzilla.redhat.com/show_bug.cgi?id=907307
    def test_virt_possible_arch(self):
        for arch in [u"i386", u"x86_64"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe = data_setup.create_recipe(dt)
            data_setup.create_job_for_recipes([recipe])
            self.assertVirtPossible(recipe, "virt precluded for %s" % arch)

    def test_virt_precluded_unsupported_arch(self):
        for arch in [u"ppc", u"ppc64", u"s390", u"s390x"]:
            dt = data_setup.create_distro_tree(arch=arch)
            recipe = data_setup.create_recipe(dt)
            data_setup.create_job_for_recipes([recipe])
            msg = "%s did not preclude virt" % arch
            self.assertVirtPrecluded(recipe, msg)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136144
    def test_hostRequires_force_precludes_virt(self):
        recipe = data_setup.create_recipe()
        recipe.host_requires = u'<hostRequires force="somesystem.example.invalid"/>'
        data_setup.create_job_for_recipes([recipe])
        self.assertVirtPrecluded(recipe, 'force="" should preclude virt')


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

    def _advance_recipe_states(self, recipes):
        # Advance some of the recipes through their state machine
        recipes[3].abort()
        for i in range(3):
            recipes[i].process()
        for i in range(2):
            recipes[i].queue()
        recipes[0].schedule()
        for recipe in recipes:
            recipe.recipeset.job.update_status()
        return {u'new': len(recipes)-4,  u'processed': 1, u'queued': 1,
                u'scheduled': 1, u'waiting': 0, u'running': 0, u'reserved': 0}

    def test_get_queue_stats(self):
        expected_stats = {u'new': 0,  u'processed': 0, u'queued': 0,
                          u'scheduled': 0, u'waiting': 0, u'running': 0, 
                          u'reserved': 0}
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
                         u'scheduled': 0, u'waiting': 0, u'running': 0, 
                         u'reserved':0}

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

        guestxml = guest_recipe.to_xml().toxml()
        self.assert_('location="nfs://something:/somewhere"' in guestxml, guestxml)
        self.assert_('nfs_location="nfs://something:/somewhere"' in guestxml, guestxml)
        self.assert_('http_location="http://something/somewhere"' in guestxml, guestxml)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691666
    def test_guestname(self):
        job_1 = data_setup.create_job(num_guestrecipes=1)
        guest_recipe_1 = job_1.recipesets[0].recipes[0].guests[0]
        job_2 = data_setup.create_job(num_guestrecipes=1, guestname=u'blueguest')
        guest_recipe_2 = job_2.recipesets[0].recipes[0].guests[0]
        session.flush()

        guestxml_1 = guest_recipe_1.to_xml().toxml()
        guestxml_2 = guest_recipe_2.to_xml().toxml()
        self.assert_(u'guestname=""' in guestxml_1, guestxml_1)
        self.assert_(u'guestname="blueguest"' in guestxml_2, guestxml_2)

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
        data_setup.mark_recipe_running(recipe, virt=True)
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
        session.commit()

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
        task = data_setup.create_task(name=u'Task1')

        tasks = Task.query.filter(Task.name == u'Task1').all()
        self.assertEquals(len(tasks), 1)

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
        yb = yum.YumBase()
        yb.preconf.init_plugins = False
        if not yb.setCacheDir(force=True, reuse=False):
            self.fail('Failed to set yum cache dir')
        cachedir = os.path.dirname(os.path.dirname(yb.conf.cachedir))
        self.assert_(cachedir.startswith('/var/tmp/yum-'), cachedir)
        self.addCleanup(shutil.rmtree, cachedir)
        yb.repos.disableRepo('*')
        yb.add_enable_repo('myrepo', ['file://' + os.path.abspath(task_dir)])
        return [''.join([pkg.version, '-', pkg.rel]) for pkg, _ in
                yb.searchGenerator(['name'], [task_name])]

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

    def tearDown(self):
        session.rollback()

    def test_version_in_xml(self):
        task = data_setup.create_task(name=u'/distribution/install')
        recipe = data_setup.create_recipe(task_list=[task])
        data_setup.create_job_for_recipes([recipe])
        data_setup.mark_recipe_running(recipe)
        rt = recipe.tasks[0]
        rt.version = u'1.2-3'
        root = lxml.etree.fromstring(rt.to_xml(clone=False).toxml())
        self.assertEquals(root.get('version'), u'1.2-3')

class RecipeTaskResultTest(DatabaseTestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_short_path(self):
        task = data_setup.create_task(name=u'/distribution/install')
        rt = RecipeTask.from_task(task)
        rtr = RecipeTaskResult(recipetask=rt, path=u'/distribution/install/Sysinfo')
        self.assertEquals(rtr.short_path, u'Sysinfo')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/start')
        self.assertEquals(rtr.short_path, u'/start')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/distribution/install')
        self.assertEquals(rtr.short_path, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/distribution/install/')
        self.assertEquals(rtr.short_path, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=None)
        self.assertEquals(rtr.short_path, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=u'')
        self.assertEquals(rtr.short_path, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/')
        self.assertEquals(rtr.short_path, u'./')
        rtr = RecipeTaskResult(recipetask=rt, path=None, log='Cancelled it')
        self.assertEquals(rtr.short_path, u'Cancelled it')
        rtr = RecipeTaskResult(recipetask=rt, path=u'', log='Cancelled it')
        self.assertEquals(rtr.short_path, u'Cancelled it')
        rtr = RecipeTaskResult(recipetask=rt, path=u'/', log='Cancelled it')
        self.assertEquals(rtr.short_path, u'Cancelled it')

if __name__ == '__main__':
    unittest.main()
