import sys
import re
import time
import datetime
import unittest2 as unittest
import pkg_resources
import lxml.etree
import email
import inspect
from turbogears.database import session
from bkr.server.installopts import InstallOptions
from bkr.server import model
from bkr.server.model import System, SystemStatus, SystemActivity, TaskStatus, \
        SystemType, Job, JobCc, Key, Key_Value_Int, Key_Value_String, \
        Cpu, Numa, Provision, job_cc_table, Arch, DistroTree, \
        LabControllerDistroTree, TaskType, TaskPackage, Device, DeviceClass, \
        GuestRecipe, GuestResource, Recipe, LogRecipe, RecipeResource, \
        VirtResource, OSMajor, OSMajorInstallOptions, Watchdog, RecipeSet, \
        RecipeVirtStatus, MachineRecipe, GuestRecipe, Disk, Task, TaskResult, \
        Group, User, ActivityMixin, SystemAccessPolicy, SystemPermission, \
        RecipeTask, RecipeTaskResult
from bkr.server.bexceptions import BeakerException
from sqlalchemy.sql import not_
from sqlalchemy.exc import OperationalError
import netaddr
from bkr.inttest import data_setup, DummyVirtManager
from nose.plugins.skip import SkipTest

class SchemaSanityTest(unittest.TestCase):

    def test_all_tables_use_innodb(self):
        engine = session.get_bind(System.mapper)
        if engine.url.drivername != 'mysql':
            raise SkipTest('not using MySQL')
        for table in engine.table_names():
            self.assertEquals(engine.scalar(
                    'SELECT engine FROM information_schema.tables '
                    'WHERE table_schema = DATABASE() AND table_name = %s',
                    table), 'InnoDB')

class ActivityMixinTest(unittest.TestCase):

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


class TestSystem(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()
        session.close()

    def test_create_system_params(self):
        owner = data_setup.create_user()
        new_system = System(fqdn=u'test_fqdn', contact=u'test@email.com',
                            location=u'Brisbane', model=u'Proliant', serial=u'4534534',
                            vendor=u'Dell', type=SystemType.machine,
                            status=SystemStatus.automated,
                            owner=owner)
        session.flush()
        self.assertEqual(new_system.fqdn, 'test_fqdn')
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
        opts = system.install_options(distro_tree).combined_with(
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
        orig_markdown = model.markdown
        model.markdown = bad_markdown
        try:
            actual = system.notes[0].html
        finally:
            model.markdown = orig_markdown
        self.assertEqual(actual, note_text)


class TestSystemKeyValue(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()
        session.close()

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

class SystemPermissionsTest(unittest.TestCase):

    def setUp(self):
        session.begin()
        self.owner = data_setup.create_user()
        self.admin = data_setup.create_admin()
        self.system = data_setup.create_system(owner=self.owner, shared=False)
        self.policy = self.system.custom_access_policy
        self.unprivileged = data_setup.create_user()

    def tearDown(self):
        session.rollback()

    def test_can_change_owner(self):
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

class TestBrokenSystemDetection(unittest.TestCase):

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

class SystemAccessPolicyTest(unittest.TestCase):

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

class TestJob(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_cc_property(self):
        job = data_setup.create_job()
        session.flush()
        session.execute(job_cc_table.insert(values={'job_id': job.id,
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
                                33.333, 0, 66.667, 0)

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
                                66.667, 16.667, 16.667, 0)


class DistroTreeByFilterTest(unittest.TestCase):

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

class WatchdogTest(unittest.TestCase):

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


class DistroTreeTest(unittest.TestCase):

    def setUp(self):
        session.begin()
        self.distro_tree = data_setup.create_distro_tree(arch=u'i386')
        self.lc = data_setup.create_labcontroller()
        session.flush()

    def tearDown(self):
        session.commit()

    def test_all_systems_obeys_osmajor_exclusions(self):
        included_system = data_setup.create_system(arch=u'i386',
                lab_controller=self.lc)
        excluded_system = data_setup.create_system(arch=u'i386',
                lab_controller=self.lc,
                exclude_osmajor=[self.distro_tree.distro.osversion.osmajor])
        excluded_system.arch.append(Arch.by_name(u'x86_64'))
        session.flush()
        systems = self.distro_tree.all_systems().all()
        self.assert_(included_system in systems and
                excluded_system not in systems, systems)

    def test_all_systems_obeys_osversion_exclusions(self):
        included_system = data_setup.create_system(arch=u'i386',
                lab_controller=self.lc)
        excluded_system = data_setup.create_system(arch=u'i386',
                lab_controller=self.lc,
                exclude_osversion=[self.distro_tree.distro.osversion])
        excluded_system.arch.append(Arch.by_name(u'x86_64'))
        session.flush()
        systems = self.distro_tree.all_systems().all()
        self.assert_(included_system in systems and
                excluded_system not in systems, systems)

    def test_all_systems_matches_arch(self):
        included_system = data_setup.create_system(arch=u'i386',
                lab_controller=self.lc)
        excluded_system = data_setup.create_system(arch=u'ppc64',
                lab_controller=self.lc)
        session.flush()
        systems = self.distro_tree.all_systems().all()
        self.assert_(included_system in systems and
                excluded_system not in systems, systems)

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

class DistroTreeSystemsFilterTest(unittest.TestCase):

    def setUp(self):
        session.begin()
        self.lc = data_setup.create_labcontroller()
        self.distro_tree = data_setup.create_distro_tree(arch=u'i386')
        self.user = data_setup.create_user()
        session.flush()

    def tearDown(self):
        session.commit()

    def check_systems(self, present, absent, systems):
        for system in present:
            self.assert_(system in systems)

        for system in absent:
            self.assert_(system not in systems)

    # test cases for <group/> are in bkr.server.test.test_group_xml

    def test_autoprov(self):
        no_power = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        no_power.power = None
        no_lab = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=None)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <auto_prov value="True" />
            </hostRequires>
            """).all()
        self.assert_(no_power not in systems)
        self.assert_(no_lab not in systems)
        self.assert_(included in systems)

    def test_system_type(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, type=SystemType.prototype)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><type op="==" value="Machine" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        # Deprecated system_type
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system_type op="==" value="Machine" />
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_status(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><status op="==" value="Automated" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_lender(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                lender=u'my excluded lender')
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                lender=u'my included lender')
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><lender op="like" value="%included%" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_model(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                model=u'grover')
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                model=u'elmo')
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><model op="=" value="elmo" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_vendor(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                vendor=u'apple')
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                vendor=u'mango')
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><vendor op="!=" value="apple" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system key="vendor" op="!=" value="apple" />
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_owner(self):
        owner1 = data_setup.create_user()
        owner2 = data_setup.create_user()
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                owner=owner1)
        excluded.user = owner2
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                owner=owner2)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><owner op="=" value="%s" /></system>
            </hostRequires>
            """ % owner2.user_name).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_user(self):
        user1 = data_setup.create_user()
        user2 = data_setup.create_user()
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                owner=user2)
        excluded.user=user1
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated)
        included.user=user2
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system>
                 <user op="=" value="%s" />
                 <owner op="!=" value="%s" />
                </system>
            </hostRequires>
            """ % (user2.user_name, user2.user_name)).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    #https://bugzilla.redhat.com/show_bug.cgi?id=955868
    def test_system_added(self):

        # date times
        today = datetime.date.today()
        time_now = datetime.datetime.combine(today, datetime.time(0, 0))
        time_delta1 = datetime.datetime.combine(today, datetime.time(0, 30))
        time_tomorrow = time_now + datetime.timedelta(days=2)

        # today date
        date_today = time_now.date().isoformat()
        date_tomorrow = time_tomorrow.date().isoformat()

        sys_today1 = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, date_added=time_now)
        sys_today2 = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, date_added=time_delta1)
        sys_tomorrow = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, date_added=time_tomorrow)

        session.flush()

        # on a date
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><added op="=" value="%s" /></system>
            </hostRequires>
            """% date_today).all()

        self.assert_(sys_today1 in systems)
        self.assert_(sys_today2 in systems)
        self.assert_(sys_tomorrow not in systems)

        # not on a date
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><added op="!=" value="%s" /></system>
            </hostRequires>
            """% date_today).all()

        self.assert_(sys_today1 not in systems)
        self.assert_(sys_today2 not in systems)
        self.assert_(sys_tomorrow in systems)

        # after a date
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><added op="&gt;" value="%s" /></system>
            </hostRequires>
            """% date_today).all()

        self.assert_(sys_tomorrow in systems)
        self.assert_(sys_today1 not in systems)
        self.assert_(sys_today2 not in systems)

        # before a date
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><added op="&lt;" value="%s" /></system>
            </hostRequires>
            """% date_tomorrow).all()

        self.assert_(sys_tomorrow not in systems)
        self.assert_(sys_today1 in systems)
        self.assert_(sys_today2 in systems)


        # on a date time
        try:
            systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><added op="=" value="%s" /></system>
            </hostRequires>
            """% time_now).all()
            self.fail('Fail or Die')
        except ValueError,e:
            self.assert_('Invalid date format' in str(e), e)

    # https://bugzillaOA.redhat.com/show_bug.cgi?id=949777
    def test_system_inventory_filter(self):

        # date times
        today = datetime.date.today()
        time_now = datetime.datetime.combine(today, datetime.time(0, 0))
        time_delta1 = datetime.datetime.combine(today, datetime.time(0, 30))
        time_tomorrow = time_now + datetime.timedelta(days=1)
        time_dayafter = time_now + datetime.timedelta(days=2)

        # dates
        date_today = time_now.date().isoformat()
        date_tomorrow = time_tomorrow.date().isoformat()
        date_dayafter = time_dayafter.date().isoformat()

        not_inv = data_setup.create_system()
        inv1 = data_setup.create_system()
        inv1.date_lastcheckin = time_now
        inv2 = data_setup.create_system()
        inv2.date_lastcheckin = time_delta1
        inv3 = data_setup.create_system()
        inv3.date_lastcheckin = time_tomorrow

        session.flush()

        # not inventoried
        systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="=" value="" /> </system>
                </hostRequires>
                """).all()

        self.check_systems(present=[not_inv],
                           absent=[inv1,inv2,inv3],
                           systems=systems)
        # inventoried
        systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="!=" value="" /> </system>
                </hostRequires>
                """).all()

        self.check_systems(present=[inv1,inv2,inv3],
                           absent=[not_inv],
                           systems=systems)

        # on a particular day
        systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="=" value="%s" /> </system>
                </hostRequires>
                """ %date_today).all()

        self.check_systems(present=[inv1,inv2],
                           absent=[not_inv, inv3],
                           systems=systems)

        # on a particular day on which no machines have been inventoried
        systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="=" value="%s" /> </system>
                </hostRequires>
                """ %date_dayafter).all()

        self.assertEquals(len(systems),0)

        # not on a particular day
        systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="!=" value="%s" /> </system>
                </hostRequires>
                """ %date_today).all()

        self.check_systems(present=[inv3],
                           absent=[not_inv,inv1,inv2],
                           systems=systems)

        # after a particular day
        systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="&gt;" value="%s" /> </system>
                </hostRequires>
                """ %date_today).all()

        self.check_systems(present=[inv3],
                           absent=[not_inv, inv1, inv2],
                           systems=systems)

        # Invalid date with &gt;
        try:
            systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="&gt;" value="foo-bar-baz f:b:z" /> </system>
                </hostRequires>
                """).all()
            self.fail('Must Fail or Die')
        except ValueError, e:
            self.assert_('Invalid date format' in str(e), e)

        # Invalid date format with =
        try:
            systems = self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <system> <last_inventoried op="=" value="2013-10-10 00:00:10" /> </system>
                </hostRequires>
                """).all()
            self.fail('Must Fail or Die')
        except ValueError, e:
            self.assert_('Invalid date format' in str(e), e)

    def test_system_loaned(self):
        user1 = data_setup.create_user()
        user2 = data_setup.create_user()
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                loaned=user1, owner=user2)
        excluded.user = user2
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                loaned=user2)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system>
                 <loaned op="=" value="%s" />
                 <owner op="!=" value="%s" />
                </system>
            </hostRequires>
            """ % (user2.user_name, user2.user_name)).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_location(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                location=u'singletary')
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                location=u'rayburn')
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><location op="=" value="rayburn" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_serial(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual,
                serial=u'0u812')
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated,
                serial=u'2112')
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><serial op="=" value="2112" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_system_powertype(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.manual)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, status=SystemStatus.automated)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><powertype op="=" value="%s" /></system>
            </hostRequires>
            """ % included.power.power_type.name).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_hostname(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <hostname op="==" value="%s" />
            </hostRequires>
            """ % included.fqdn).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><name op="==" value="%s" /></system>
            </hostRequires>
            """ % included.fqdn).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_memory(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, memory=128)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, memory=1024)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <memory op="&gt;=" value="256" />
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_processors(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <cpu_count op="=" value="4" />
                </and>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                    <cpu><processors op="=" value="4" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <cpu><processors op="&gt;" value="2" /></cpu>
                    <cpu><processors op="&lt;" value="5" /></cpu>
                </and>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <cpu_count op="&gt;" value="2" />
                    <cpu_count op="&lt;" value="5" />
                </and>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_cores(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><cores op="&gt;" value="1" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_family(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><family op="=" value="10" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_model(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><model op="=" value="4" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_sockets(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><sockets op="&gt;=" value="2" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_speed(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><speed op="&gt;=" value="1500.0" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_stepping(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><stepping op="&gt;=" value="1" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_vendor(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><vendor op="like" value="%Intel" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_model(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><model_name op="like" value="%Xeon%" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_hyper(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.cpu = Cpu(processors=1, cores=1, family=21,
                           model=2, sockets=1, speed=1400.0, stepping=0,
                           vendor=u'AuthenticAMD',
                           model_name=u'AMD Opteron(tm) Processor 6386 SE ')
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.cpu = Cpu(processors=4, cores=2, family=10,
                           model=4, sockets=2, speed=2000.0, stepping=1,
                           vendor=u'GenuineIntel',
                           model_name=u'Intel(R) Xeon(R) CPU E5-4650 0 @ 2.70GHz')
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><hyper value="true" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_cpu_flags(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        excluded.cpu = Cpu(processors=1, flags=[u'ssse3', 'pae'])
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        included.cpu = Cpu(processors=1, flags=[u'ssse3', 'vmx'])
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><flag value="vmx" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><flag op="!=" value="pae" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <cpu><flag op="like" value="%vmx%" /></cpu>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_or_lab_controller(self):
        lc1 = data_setup.create_labcontroller(fqdn=u'lab1')
        lc2 = data_setup.create_labcontroller(fqdn=u'lab2')
        lc3 = data_setup.create_labcontroller(fqdn=u'lab3')
        distro_tree = data_setup.create_distro_tree()
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.lab_controller = lc1
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = lc3
        session.flush()
        systems = list(distro_tree.systems_filter(self.user, """
               <hostRequires>
                <or>
                 <hostlabcontroller op="=" value="lab1"/>
                 <hostlabcontroller op="=" value="lab2"/>
                </or>
               </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(distro_tree.systems_filter(self.user, """
               <hostRequires>
                <or>
                 <labcontroller op="=" value="lab1"/>
                 <labcontroller op="=" value="lab2"/>
                </or>
               </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=831448
    def test_hostlabcontroller_notequal(self):
        desirable_lc = data_setup.create_labcontroller()
        undesirable_lc = data_setup.create_labcontroller()
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=desirable_lc)
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=undesirable_lc)
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <hostlabcontroller op="!=" value="%s" />
                </hostRequires>
                """ % undesirable_lc.fqdn))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
                <hostRequires>
                    <labcontroller op="!=" value="%s" />
                </hostRequires>
                """ % undesirable_lc.fqdn))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_arch_equal(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        included.arch.append(Arch.by_name(u'x86_64'))
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <arch op="=" value="x86_64" />
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><arch op="=" value="x86_64" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_arch_notequal(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        excluded.arch.append(Arch.by_name(u'x86_64'))
        included = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        session.flush()
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <arch op="!=" value="x86_64" />
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system><arch op="!=" value="x86_64" /></system>
            </hostRequires>
            """).all()
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_numa_node_count(self):
        excluded = data_setup.create_system(arch=u'i386', shared=True)
        excluded.lab_controller = self.lc
        excluded.numa = Numa(nodes=1)
        included = data_setup.create_system(arch=u'i386', shared=True)
        included.numa = Numa(nodes=64)
        included.lab_controller = self.lc
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <numa_node_count op=">=" value="32" />
                </and>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <system>
                    <numanodes op=">=" value="32" />
                </system>
            </hostRequires>
            """))
        self.assert_(excluded not in systems)
        self.assert_(included in systems)

    def test_key_equal(self):
        module_key = Key.by_name(u'MODULE')
        with_cciss = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        with_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_cciss = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        without_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'ida'),
                Key_Value_String(module_key, u'kvm')])
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <key_value key="MODULE" op="==" value="cciss"/>
            </hostRequires>
            """))
        self.assert_(with_cciss in systems)
        self.assert_(without_cciss not in systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=679879
    def test_key_notequal(self):
        module_key = Key.by_name(u'MODULE')
        with_cciss = data_setup.create_system(arch=u'i386', shared=True)
        with_cciss.lab_controller = self.lc
        with_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_cciss = data_setup.create_system(arch=u'i386', shared=True)
        without_cciss.lab_controller = self.lc
        without_cciss.key_values_string.extend([
                Key_Value_String(module_key, u'ida'),
                Key_Value_String(module_key, u'kvm')])
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <key_value key="MODULE" op="!=" value="cciss"/>
                </and>
            </hostRequires>
            """))
        self.assert_(with_cciss not in systems)
        self.assert_(without_cciss in systems)

    def test_key_present(self):
        module_key = Key.by_name(u'MODULE')
        with_module = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        with_module.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_module = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <key_value key="MODULE" op="==" />
            </hostRequires>
            """))
        self.assert_(with_module in systems)
        self.assert_(without_module not in systems)

    def test_key_absent(self):
        module_key = Key.by_name(u'MODULE')
        with_module = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        with_module.key_values_string.extend([
                Key_Value_String(module_key, u'cciss'),
                Key_Value_String(module_key, u'kvm')])
        without_module = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <key_value key="MODULE" op="!=" />
            </hostRequires>
            """))
        self.assert_(with_module not in systems)
        self.assert_(without_module in systems)
        # ... or using <not/> is a saner way to do it:
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <not><key_value key="MODULE" /></not>
            </hostRequires>
            """))
        self.assert_(with_module not in systems)
        self.assert_(without_module in systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=729156
    def test_keyvalue_does_not_cause_duplicate_rows(self):
        system = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        disk_key = Key.by_name(u'DISK')
        system.key_values_int.extend([
                Key_Value_Int(disk_key, 30718),
                Key_Value_Int(disk_key, 140011),
                Key_Value_Int(disk_key, 1048570)])
        session.flush()
        query = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <system><name op="=" value="%s" /></system>
                    <key_value key="DISK" op="&gt;" value="9000" />
                </and>
            </hostRequires>
            """ % system.fqdn)
        self.assertEquals(len(query.all()), 1)
        # with the bug this count comes out as 3 instead of 1,
        # which doesn't sound so bad...
        # but when it's 926127 instead of 278, that's bad
        self.assertEquals(query.count(), 1)

    # https://bugzilla.redhat.com/show_bug.cgi?id=824050
    def test_multiple_nonexistent_keys(self):
        query = self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <key_value key="NOTEXIST1" op="=" value="asdf"/>
                    <key_value key="NOTEXIST2" op="=" value="asdf"/>
                </and>
            </hostRequires>
            """)
        query.all() # don't care about the results, just that it doesn't break

    # https://bugzilla.redhat.com/show_bug.cgi?id=714974
    def test_hypervisor(self):
        baremetal = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, hypervisor=None)
        kvm = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc, hypervisor=u'KVM')
        session.flush()
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                    <system><hypervisor op="=" value="KVM" /></system>
            </hostRequires>
            """))
        self.assert_(baremetal not in systems)
        self.assert_(kvm in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <hypervisor op="=" value="KVM" />
                </and>
            </hostRequires>
            """))
        self.assert_(baremetal not in systems)
        self.assert_(kvm in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                    <system><hypervisor op="=" value="" /></system>
            </hostRequires>
            """))
        self.assert_(baremetal in systems)
        self.assert_(kvm not in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <and>
                    <hypervisor op="=" value="" />
                </and>
            </hostRequires>
            """))
        self.assert_(baremetal in systems)
        self.assert_(kvm not in systems)
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires/>
            """))
        self.assert_(baremetal in systems)
        self.assert_(kvm in systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=731615
    def test_filtering_by_device(self):
        network_class = data_setup.create_device_class(u'NETWORK')
        with_e1000 = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        with_e1000.devices.append(data_setup.create_device(
                device_class_id=network_class.id,
                vendor_id=u'8086', device_id=u'107c',
                subsys_vendor_id=u'8086', subsys_device_id=u'1376',
                bus=u'pci', driver=u'e1000',
                description=u'82541PI Gigabit Ethernet Controller'))
        with_tg3 = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        with_tg3.devices.append(data_setup.create_device(
                device_class_id=network_class.id,
                vendor_id=u'14e4', device_id=u'1645',
                subsys_vendor_id=u'10a9', subsys_device_id=u'8010',
                bus=u'pci', driver=u'tg3',
                description=u'NetXtreme BCM5701 Gigabit Ethernet'))
        session.flush()

        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <device op="=" driver="e1000" />
            </hostRequires>
            """))
        self.assert_(with_e1000 in systems)
        self.assert_(with_tg3 not in systems)

        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <device op="like" description="82541PI%" />
            </hostRequires>
            """))
        self.assert_(with_e1000 in systems)
        self.assert_(with_tg3 not in systems)

        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <device op="=" type="network" vendor_id="8086" />
            </hostRequires>
            """))
        self.assert_(with_e1000 in systems)
        self.assert_(with_tg3 not in systems)

        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <device op="=" vendor_id="14E4" device_id="1645" />
            </hostRequires>
            """))
        self.assert_(with_e1000 not in systems)
        self.assert_(with_tg3 in systems)

        # this filter does nothing, but at least it shouldn't explode
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <device op="=" />
            </hostRequires>
            """))
        self.assert_(with_e1000 in systems)
        self.assert_(with_tg3 in systems)

    # https://bugzilla.redhat.com/show_bug.cgi?id=766919
    def test_filtering_by_disk(self):
        small_disk = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        small_disk.disks[:] = [Disk(size=8000000000,
                sector_size=512, phys_sector_size=512)]
        big_disk = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        big_disk.disks[:] = [Disk(size=2000000000000,
                sector_size=4096, phys_sector_size=4096)]
        two_disks = data_setup.create_system(arch=u'i386', shared=True,
                lab_controller=self.lc)
        two_disks.disks[:] = [
                Disk(size=500000000000, sector_size=512, phys_sector_size=512),
                Disk(size=8000000000, sector_size=4096, phys_sector_size=4096)]
        session.flush()

        # criteria inside the same <disk/> element apply to a single disk
        # and are AND'ed by default
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <disk>
                    <size op="&gt;" value="10" units="GB" />
                    <phys_sector_size op="=" value="4" units="KiB" />
                </disk>
            </hostRequires>
            """))
        self.assert_(small_disk not in systems)
        self.assert_(big_disk in systems)
        self.assert_(two_disks not in systems)

        # separate <disk/> elements can match separate disks
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <disk><size op="&gt;" value="10" units="GB" /></disk>
                <disk><phys_sector_size op="=" value="4" units="KiB" /></disk>
            </hostRequires>
            """))
        self.assert_(small_disk not in systems)
        self.assert_(big_disk in systems)
        self.assert_(two_disks in systems)

        # <not/> combined with a negative filter can be used to filter against 
        # all disks (e.g. "give me systems with only 512-byte-sector disks")
        systems = list(self.distro_tree.systems_filter(self.user, """
            <hostRequires>
                <not><disk><sector_size op="!=" value="512" /></disk></not>
            </hostRequires>
            """))
        self.assert_(small_disk in systems)
        self.assert_(big_disk not in systems)
        self.assert_(two_disks not in systems)

class OSMajorTest(unittest.TestCase):

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

class UserTest(unittest.TestCase):

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

class GroupTest(unittest.TestCase):

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


class TaskTypeTest(unittest.TestCase):

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


class RecipeTest(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_roles_to_xml(self):
        dt = data_setup.create_distro_tree()
        lc = data_setup.create_labcontroller()
        systems = [
            data_setup.create_system(fqdn=u'server.roles_to_xml', lab_controller=lc),
            data_setup.create_system(fqdn=u'clientone.roles_to_xml', lab_controller=lc),
            data_setup.create_system(fqdn=u'clienttwo.roles_to_xml', lab_controller=lc),
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
                '<role value="CLIENTONE"><system value="clientone.roles_to_xml"/></role>'
                '<role value="CLIENTTWO"><system value="clienttwo.roles_to_xml"/></role>'
                '<role value="SERVER"><system value="server.roles_to_xml"/></role>'
                '</roles>' in xml, xml)


class CheckDynamicVirtTest(unittest.TestCase):

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


class MachineRecipeTest(unittest.TestCase):

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
                u'scheduled': 1, u'waiting': 0, u'running': 0}

    def test_get_queue_stats(self):
        expected_stats = {u'new': 0,  u'processed': 0, u'queued': 0,
                          u'scheduled': 0, u'waiting': 0, u'running': 0}
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
                         u'scheduled': 0, u'waiting': 0, u'running': 0}
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


class GuestRecipeTest(unittest.TestCase):

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

class MACAddressAllocationTest(unittest.TestCase):

    def setUp(self):
        self.orig_VirtManager = model.VirtManager
        model.VirtManager = DummyVirtManager
        session.begin()
        # Other tests might have left behind running recipes using MAC
        # addresses, let's cancel them all
        running = RecipeSet.query.filter(not_(RecipeSet.status.in_(
                [s for s in TaskStatus if s.finished])))
        for rs in running:
            rs.cancel()
            rs.job.update_status()

    def tearDown(self):
        model.VirtManager = self.orig_VirtManager
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

    def test_virt_and_guest_resources(self):
        # One GuestResource ...
        first_job = data_setup.create_job(num_guestrecipes=1)
        data_setup.mark_job_running(first_job)
        self.assertEquals(first_job.recipesets[0].recipes[0].guests[0].resource.mac_address,
                    netaddr.EUI('52:54:00:00:00:00'))
        # ... and one VirtResource
        second_job = data_setup.create_job()
        data_setup.mark_recipe_running(second_job.recipesets[0].recipes[0], virt=True)
        self.assertEquals(second_job.recipesets[0].recipes[0].resource.mac_address,
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

class LogRecipeTest(unittest.TestCase):

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


class TaskPackageTest(unittest.TestCase):

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

class DeviceClassTest(unittest.TestCase):

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

class DeviceTest(unittest.TestCase):

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

class TaskTest(unittest.TestCase):

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

        task = data_setup.create_task(name='Task1')
        task = data_setup.create_task(name='Task1')

        tasks = Task.query.filter(Task.name == 'Task1').all()
        self.assertEquals(len(tasks), 1)

class RecipeTaskResultTest(unittest.TestCase):

    def test_short_path(self):
        task = data_setup.create_task(name=u'/distribution/install')
        rt = RecipeTask(task=task)
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
