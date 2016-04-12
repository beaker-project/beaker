
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pkg_resources
import datetime
from decimal import Decimal
from turbogears.database import session
from sqlalchemy.sql import text
from bkr.server import dynamic_virt
from bkr.server.model import System, RecipeTask, Cpu, SystemStatus, \
    SystemActivity, TaskPriority, RecipeSetActivity, VirtResource, \
    GuestResource
from bkr.inttest import data_setup, DatabaseTestCase

class ReportingQueryTest(DatabaseTestCase):

    def setUp(self):
        session.begin()
        self.addCleanup(session.rollback)
        # Other tests could have also created VirtResources and GuestResources, 
        # we hack them up so they don't interfere with the min/max/avg we are 
        # expecting here.
        for resource in VirtResource.query:
            resource.recipe.start_time = None
            if resource.recipe.installation:
                resource.recipe.installation.install_started = None
                resource.recipe.installation.install_finished = None
        for resource in GuestResource.query:
            resource.recipe.start_time = None
            if resource.recipe.installation:
                resource.recipe.installation.install_started = None
                resource.recipe.installation.install_finished = None
        session.flush()

    def execute_reporting_query(self, name):
        sql = pkg_resources.resource_string('bkr.server', 'reporting-queries/%s.sql' % name)
        return session.connection(System).execute(text(sql))

    def test_wait_duration_by_resource(self):
        system_recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([system_recipe])
        virt_recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([virt_recipe])
        virt_recipe2 = data_setup.create_recipe()
        data_setup.create_job_for_recipes([virt_recipe2])

        data_setup.mark_recipe_complete(virt_recipe, virt=True)
        data_setup.mark_recipe_complete(virt_recipe2, virt=True)
        data_setup.mark_recipe_complete(system_recipe)

        system_recipe2 = data_setup.create_recipe()
        data_setup.create_job_for_recipes([system_recipe2])
        data_setup.mark_recipe_complete(system_recipe2, system=system_recipe.resource.system)

        one_hour = datetime.timedelta(hours=1)
        two_hours = datetime.timedelta(hours=2)
        three_hours = datetime.timedelta(hours=3)

        virt_recipe.resource.recipe.start_time = virt_recipe.resource.recipe.recipeset.queue_time + one_hour
        virt_recipe2.resource.recipe.start_time = virt_recipe2.resource.recipe.recipeset.queue_time + two_hours

        system_recipe.resource.recipe.start_time = system_recipe.resource.recipe.recipeset.queue_time + one_hour
        system_recipe2.resource.recipe.start_time = system_recipe2.resource.recipe.recipeset.queue_time + three_hours
        session.flush()

        rows = self.execute_reporting_query('wait-duration-by-resource')
        all_rows = rows.fetchall()
        virt_rows = [row for row in all_rows if row.fqdn == 'All OpenStack']
        system_rows = [row for row in all_rows if row.fqdn in (system_recipe.resource.fqdn, system_recipe2.resource.fqdn)]

        self.assertEquals(len(virt_rows), 1, virt_rows)
        self.assertEquals(virt_rows[0].min_wait_hours, 1)
        self.assertEquals(virt_rows[0].max_wait_hours, 2)
        self.assertEquals(virt_rows[0].avg_wait_hours, Decimal('1.5'))

        self.assertEquals(len(system_rows), 1, system_rows)
        self.assertEquals(system_rows[0].min_wait_hours, 1)
        self.assertEquals(system_rows[0].max_wait_hours, 3)
        self.assertEquals(system_rows[0].avg_wait_hours, 2)

    def test_install_duration_by_resource(self):
        system_recipe = data_setup.create_recipe()
        guest_recipe = data_setup.create_guestrecipe(host=system_recipe)
        data_setup.mark_job_complete(
                data_setup.create_job_for_recipes([system_recipe, guest_recipe]))
        virt_recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([virt_recipe])
        virt_recipe2 = data_setup.create_recipe()
        data_setup.create_job_for_recipes([virt_recipe2])
        data_setup.mark_recipe_complete(virt_recipe, virt=True)
        data_setup.mark_recipe_complete(virt_recipe2, virt=True)

        system_recipe2 = data_setup.create_recipe()
        guest_recipe2 = data_setup.create_guestrecipe(host=system_recipe2)
        job2 = data_setup.create_job_for_recipes([system_recipe2, guest_recipe2])
        data_setup.mark_job_complete(job2, system=system_recipe.resource.system)

        one_hour = datetime.timedelta(hours=1)
        two_hours = datetime.timedelta(hours=2)
        three_hours = datetime.timedelta(hours=3)

        virt_recipe.installation.install_finished = virt_recipe.installation.install_started + one_hour
        virt_recipe2.installation.install_finished = virt_recipe2.installation.install_started + two_hours

        guest_recipe.installation.install_finished = guest_recipe.installation.install_started + two_hours
        guest_recipe2.installation.install_finished = guest_recipe2.installation.install_started + three_hours

        system_recipe.installation.install_finished = system_recipe.installation.install_started + one_hour
        system_recipe2.installation.install_finished = system_recipe2.installation.install_started + three_hours
        session.flush()

        rows = self.execute_reporting_query('install-duration-by-resource')
        all_rows = rows.fetchall()
        guest_rows = [row for row in all_rows if row.fqdn == 'All Guest']
        virt_rows = [row for row in all_rows if row.fqdn == 'All OpenStack']
        system_rows = [row for row in all_rows if row.fqdn == system_recipe.resource.fqdn]

        self.assertEquals(len(virt_rows), 1, virt_rows)
        self.assertEquals(virt_rows[0].min_install_hours, 1)
        self.assertEquals(virt_rows[0].max_install_hours, 2)
        self.assertEquals(virt_rows[0].avg_install_hours, Decimal('1.5'))

        self.assertEquals(len(guest_rows), 1, guest_rows)
        self.assertEquals(guest_rows[0].min_install_hours, 2)
        self.assertEquals(guest_rows[0].max_install_hours, 3)
        self.assertEquals(guest_rows[0].avg_install_hours, Decimal('2.5'))

        self.assertEquals(len(system_rows), 1, system_rows)
        self.assertEquals(system_rows[0].min_install_hours, 1)
        self.assertEquals(system_rows[0].max_install_hours, 3)
        self.assertEquals(system_rows[0].avg_install_hours, Decimal('2.0'))

    def test_resource_install_failures(self):

        # Get existing state to later compare against
        rows = self.execute_reporting_query('install-failure-count-by-resource')
        all_rows = [row for row in rows]
        guest_rows = [row for row in all_rows if row.fqdn == 'All Guest']
        virt_rows = [row for row in all_rows if row.fqdn == 'All OpenStack']
        existing_failed_guests = guest_rows[0].failed_recipes
        existing_failed_virt = virt_rows[0].failed_recipes

        system_recipe = data_setup.create_recipe()
        guest_recipe = data_setup.create_guestrecipe(host=system_recipe)
        virt_recipe = data_setup.create_recipe()
        job = data_setup.create_job_for_recipes([guest_recipe, virt_recipe, system_recipe])

        data_setup.mark_recipe_installing(virt_recipe, virt=True)
        data_setup.mark_recipe_installing(system_recipe)
        data_setup.mark_recipe_installing(guest_recipe)
        session.flush()

        # Test we don't count runinng recipes
        rows = self.execute_reporting_query('install-failure-count-by-resource')
        all_rows = [row for row in rows]
        system_rows = [row for row in all_rows if row.fqdn == system_recipe.resource.fqdn]

        self.assertEquals(len(virt_rows), 1, virt_rows)
        self.assertEquals(existing_failed_virt, virt_rows[0].failed_recipes)

        self.assertEquals(len(guest_rows), 1, guest_rows)
        self.assertEquals(existing_failed_guests, guest_rows[0].failed_recipes)

        self.assertEquals(len(system_rows), 1, system_rows)
        self.assertEquals(system_rows[0].failed_recipes, 0)

        # Test completed recipes
        job.abort()
        job.update_status()
        session.flush()
        rows = self.execute_reporting_query('install-failure-count-by-resource')
        all_rows = [row for row in rows]
        guest_rows = [row for row in all_rows if row.fqdn == 'All Guest']
        virt_rows = [row for row in all_rows if row.fqdn == 'All OpenStack']
        system_rows = [row for row in all_rows if row.fqdn == system_recipe.resource.fqdn]

        self.assertEquals(len(virt_rows), 1, virt_rows)
        self.assertEquals(virt_rows[0].failed_recipes, existing_failed_virt + 1)

        self.assertEquals(len(guest_rows), 1, guest_rows)
        self.assertEquals(guest_rows[0].failed_recipes, existing_failed_guests + 1)

        self.assertEquals(len(system_rows), 1, system_rows)
        self.assertEquals(system_rows[0].failed_recipes, 1)

    # https://bugzilla.redhat.com/show_bug.cgi?id=877264
    def test_recipe_hours(self):
        user = data_setup.create_user()
        # recipes/reservations straddle the boundary of the reporting period
        # to test we clamp them properly
        data_setup.create_completed_job(owner=user,
                distro_tree=data_setup.create_distro_tree(arch=u'ia64'),
                start_time=datetime.datetime(2012, 9, 30, 12, 0, 0),
                finish_time=datetime.datetime(2012, 10, 1, 1, 30, 0))
        data_setup.create_completed_job(owner=user,
                distro_tree=data_setup.create_distro_tree(arch=u'ppc64'),
                start_time=datetime.datetime(2012, 10, 31, 22, 0, 0),
                finish_time=datetime.datetime(2012, 11, 1, 10, 0, 0))
        session.flush()
        rows = self.execute_reporting_query('recipe-hours-by-user-arch')
        user_rows = [row for row in rows if row.username == user.user_name]
        self.assertEquals(len(user_rows), 2, user_rows)
        self.assertEquals(user_rows[0].arch, 'ia64')
        self.assertEquals(user_rows[0].recipe_hours, Decimal('1.5'))
        self.assertEquals(user_rows[1].arch, 'ppc64')
        self.assertEquals(user_rows[1].recipe_hours, Decimal('2.0'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=877264
    def test_machine_hours(self):
        user = data_setup.create_user()
        # recipes/reservations straddle the boundary of the reporting period
        # to test we clamp them properly
        data_setup.create_completed_job(owner=user,
                distro_tree=data_setup.create_distro_tree(arch=u'ia64'),
                start_time=datetime.datetime(2012, 9, 30, 23, 0, 0),
                finish_time=datetime.datetime(2012, 10, 1, 1, 0, 0))
        data_setup.create_manual_reservation(user=user,
                system=data_setup.create_system(arch=u'ia64'),
                start=datetime.datetime(2012, 10, 31, 22, 30, 0),
                finish=datetime.datetime(2012, 11, 1, 1, 0, 0))
        data_setup.create_completed_job(owner=user,
                distro_tree=data_setup.create_distro_tree(arch=u'ppc64'),
                start_time=datetime.datetime(2012, 9, 30, 20, 0, 0),
                finish_time=datetime.datetime(2012, 10, 1, 2, 0, 0))
        data_setup.create_manual_reservation(user=user,
                system=data_setup.create_system(arch=u'ppc64'),
                start=datetime.datetime(2012, 10, 31, 23, 0, 0),
                finish=datetime.datetime(2012, 11, 1, 10, 0, 0))
        session.flush()
        rows = self.execute_reporting_query('machine-hours-by-user-arch')
        user_rows = [row for row in rows if row.username == user.user_name]
        self.assertEquals(len(user_rows), 2, user_rows)
        self.assertEquals(user_rows[0].arch, 'ia64')
        self.assertEquals(user_rows[0].machine_hours, Decimal('2.5'))
        self.assertEquals(user_rows[1].arch, 'ppc64')
        self.assertEquals(user_rows[1].machine_hours, Decimal('3.0'))

    #https://bugzilla.redhat.com/show_bug.cgi?id=1117681
    def test_machine_utilization(self):
        #
        # Note: If test relies on an SQL script with hard coded time stamps in
        # 2002 or no finish reservation times.
        #
        system1 = data_setup.create_system()
        system2 = data_setup.create_system()
        system3 = data_setup.create_system()
        data_setup.create_manual_reservation(system=system1,
                                             start=datetime.datetime(2002, 6, 2, 22, 30, 0),
                                             finish=datetime.datetime(2002, 6, 3, 22, 30, 0))
        data_setup.create_manual_reservation(system=system2,
                                             start=datetime.datetime(2002, 5, 2, 22, 30, 0))
        data_setup.create_manual_reservation(system=system3,
                                             start=datetime.datetime(2002, 5, 2, 22, 30, 0),
                                             finish=datetime.datetime(2002, 5, 3, 22, 30, 0))
        session.flush()
        rows = [row for row in self.execute_reporting_query('machine-utilization')]
        self.assertEquals(len(rows), 2, rows)
        self.assertIn((system1.fqdn, Decimal('0.0333')), rows)
        self.assertIn((system2.fqdn, Decimal('1.0000')), rows)
        # system3 should not appear
        self.assertNotIn(system3.fqdn, [row[0] for row in rows])

    # https://bugzilla.redhat.com/show_bug.cgi?id=877272
    def test_task_durations(self):
        short_task = data_setup.create_task()
        long_task = data_setup.create_task()
        r = data_setup.create_recipe(task_list=[short_task, long_task])
        data_setup.mark_job_complete(
                data_setup.create_job_for_recipes([r]))
        r.tasks[0].start_time = datetime.datetime(2012, 10, 15, 10, 54, 0)
        r.tasks[0].finish_time = datetime.datetime(2012, 10, 15, 11, 0, 0)
        r.tasks[1].start_time = datetime.datetime(2012, 10, 15, 11, 0, 0)
        r.tasks[1].finish_time = datetime.datetime(2012, 10, 15, 21, 0, 0)
        session.flush()
        rows = list(self.execute_reporting_query('task-durations-by-arch'))
        short_task_row, = [row for row in rows if row.task == short_task.name]
        self.assertEquals(short_task_row.executions, 1)
        self.assertEquals(short_task_row.avg_duration, Decimal('0.1'))
        long_task_row, = [row for row in rows if row.task == long_task.name]
        self.assertEquals(long_task_row.executions, 1)
        self.assertEquals(long_task_row.avg_duration, Decimal('10.0'))

    def test_job_priority_changes(self):
        user1 = data_setup.create_user()
        user2 = data_setup.create_user()
        job1 = data_setup.create_job(owner=user1)
        job2 = data_setup.create_job(owner=user1)
        job3 = data_setup.create_job(owner=user2)
        job4 = data_setup.create_job(owner=user2)

        for j in [job1, job2, job3]:
            for rs in j.recipesets:
                activity = RecipeSetActivity(j.owner,
                                             'TEST',
                                             'Changed',
                                             'Priority',
                                             rs.priority.value,
                                             TaskPriority.high)
                activity.created = datetime.datetime(year=2012,
                                                     month=10,
                                                     day=10)
                rs.activity.append(activity)
        session.flush()

        rows = self.execute_reporting_query('job-priority-changes-by-user')
        all_rows = rows.fetchall()
        user1_rows = [row for row in all_rows if row.user_name == user1.user_name]
        user2_rows = [row for row in all_rows if row.user_name == user2.user_name]

        self.assertTrue(user1_rows[0].number_of_jobs_changed, 2)
        self.assertTrue(user2_rows[0].number_of_jobs_changed, 1)


    # https://bugzilla.redhat.com/show_bug.cgi?id=193142
    def test_systems_by_cpu_type(self):
        vendor = u'AcmeCorp'
        common_cpu_family = 1
        common_cpu_stepping = 2
        rare_cpu_family = 3
        rare_cpu_stepping = 4
        for _ in range(2):
            data_setup.create_system().cpu = Cpu(vendor=vendor, model=1,
                    family=rare_cpu_family, stepping=rare_cpu_stepping)
        for _ in range(20):
            data_setup.create_system().cpu = Cpu(vendor=vendor, model=1,
                    family=common_cpu_family, stepping=common_cpu_stepping)
        data_setup.create_system(status=SystemStatus.removed).cpu = \
            Cpu(vendor=vendor)
        data_setup.create_system().cpu = None # un-inventoried
        session.flush()
        rows = list(self.execute_reporting_query('system-count-by-cpu'))
        # un-inventoried systems should show up at the top
        self.assertEquals(rows[0].cpu_vendor, None)
        self.assertEquals(rows[0].cpu_model, None)
        self.assertEquals(rows[0].cpu_family, None)
        self.assertEquals(rows[0].cpu_stepping, None)
        self.assert_(rows[0].system_count >= 1, rows[0])
        # check for fake CPUs created above
        vendor_rows = [row for row in rows if row.cpu_vendor == vendor]
        self.assertEquals(len(vendor_rows), 2, vendor_rows)
        self.assertEquals(vendor_rows[0].cpu_model, 1)
        self.assertEquals(vendor_rows[0].cpu_family, common_cpu_family)
        self.assertEquals(vendor_rows[0].cpu_stepping, common_cpu_stepping)
        self.assertEquals(vendor_rows[0].system_count, 20)
        self.assertEquals(vendor_rows[1].cpu_model, 1)
        self.assertEquals(vendor_rows[1].cpu_family, rare_cpu_family)
        self.assertEquals(vendor_rows[1].cpu_stepping, rare_cpu_stepping)
        self.assertEquals(vendor_rows[1].system_count, 2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=193142
    def test_systems_by_cpu_core_count(self):
        for _ in range(3):
            data_setup.create_system(arch=u'i386').cpu = Cpu(cores=39)
        for _ in range(3):
            data_setup.create_system(arch=u'i386').cpu = Cpu(cores=41)
        data_setup.create_system(arch=u'i386', memory=None) # un-inventoried
        session.flush()
        system_counts = dict(((arch, cpu_cores), count) for arch, cpu_cores, count in
                self.execute_reporting_query('system-count-by-arch-cpu-cores'))
        self.assert_(system_counts[('i386', None)] >= 1, system_counts)
        self.assert_(system_counts[('i386', 39)] >= 3, system_counts)
        self.assert_(system_counts[('i386', 41)] >= 3, system_counts)

    # https://bugzilla.redhat.com/show_bug.cgi?id=193142
    def test_systems_by_vendor(self):
        common_vendor = u'Pink Slime Corp.'
        rare_vendor = u'Quality Meats, Inc.'
        for _ in range(2):
            data_setup.create_system().vendor = rare_vendor
        for _ in range(20):
            data_setup.create_system().vendor = common_vendor
        data_setup.create_system(status=SystemStatus.removed)\
            .vendor = common_vendor
        data_setup.create_system().vendor = None # un-inventoried
        session.flush()
        system_counts = dict((vendor, count) for vendor, count in
                self.execute_reporting_query('system-count-by-vendor'))
        self.assert_(system_counts[None] >= 1, system_counts[None])
        self.assertEquals(system_counts[rare_vendor], 2)
        self.assertEquals(system_counts[common_vendor], 20)

    # https://bugzilla.redhat.com/show_bug.cgi?id=193142
    def test_systems_by_memory(self):
        # system.memory is in MB but the report rounds to GB
        for _ in range(3):
            data_setup.create_system(arch=u'i386', memory=39 * 1024)
        for _ in range(3):
            data_setup.create_system(arch=u'i386', memory=41 * 1024)
        data_setup.create_system(arch=u'i386', memory=None) # un-inventoried
        session.flush()
        system_counts = dict(((arch, memory_gb), count) for arch, memory_gb, count in
                self.execute_reporting_query('system-count-by-arch-memory-gb'))
        self.assert_(system_counts[('i386', None)] >= 1, system_counts)
        self.assert_(system_counts[('i386', 39)] >= 3, system_counts)
        self.assert_(system_counts[('i386', 41)] >= 3, system_counts)

    # https://bugzilla.redhat.com/show_bug.cgi?id=193142
    def test_system_age(self):
        system = data_setup.create_system(date_added=
                datetime.datetime.utcnow() - datetime.timedelta(days=100),
                lab_controller=data_setup.create_labcontroller())
        for _ in range(5):
            data_setup.create_completed_job(system=system)
        session.flush()
        row, = [row for row in self.execute_reporting_query('system-age')
                if row.fqdn == system.fqdn]
        self.assertEquals(row.age_days, 100)
        self.assertEquals(row.recipe_count, 5)

    # https://bugzilla.redhat.com/show_bug.cgi?id=741960
    def test_system_breakages(self):
        system = data_setup.create_system()
        data_setup.create_system_status_history(system, [
            (SystemStatus.automated, datetime.datetime(2012, 10, 1,  0, 0)),
            (SystemStatus.broken,    datetime.datetime(2012, 10, 5,  0, 0)),
            (SystemStatus.automated, datetime.datetime(2012, 10, 5,  8, 0)),
            (SystemStatus.broken,    datetime.datetime(2012, 10, 10, 0, 0)),
        ])
        for _ in range(3):
            system.activity.append(SystemActivity(user=data_setup.create_user(),
                    created=datetime.datetime(2012, 10, 15, 0, 0),
                    service=u'testdata', action=u'Reported problem',
                    field_name=u'Status', old_value=None,
                    new_value=u'Why does it always b0rk?'))
        session.flush()
        row, = [row for row in self.execute_reporting_query('system-breakages')
                if row.fqdn == system.fqdn]
        self.assertEquals(row.breakage_count, 2)
        self.assertEquals(row.problem_report_count, 3)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1281587
    def test_cee_ops_provided_queries(self):
        # CEE Ops is a team within Red Hat who relies heavily on Beaker. These 
        # queries are used by their tooling to integrate with Beaker's 
        # inventory. The queries are covered here in our test suite so that 
        # they will know if any Beaker schema changes will affect these 
        # queries.

        cee_users = data_setup.create_group(group_name=u'cee-users')
        cee_user = data_setup.create_user(user_name=u'billybob')
        cee_users.add_member(cee_user)
        # Create a system which has been manually reserved
        reserved_system = data_setup.create_system(fqdn=u'gsslab.reserved', status='Manual')
        data_setup.create_manual_reservation(reserved_system, user=cee_user,
                start=datetime.datetime(2016, 1, 1, 0, 0))
        # Create a system which is loaned out
        loaned_system = data_setup.create_system(fqdn=u'gsslab.loaned', status='Manual')
        data_setup.create_system_loan(loaned_system, user=cee_user,
                start=datetime.datetime(2016, 1, 2, 0, 0))
        # Create a system which has been provisioned with RHEL7.1
        provisioned_system = data_setup.create_system(fqdn=u'gsslab.provisioned',
                status='Automated', lab_controller=data_setup.create_labcontroller())
        recipe = data_setup.create_recipe(distro_name=u'RHEL-7.1', variant=u'Server')
        data_setup.create_job_for_recipes([recipe], owner=cee_user)
        data_setup.mark_recipe_complete(recipe, system=provisioned_system)
        # Create a non-CEE system which has been provisioned 20 times
        noncee_provisioned_system = data_setup.create_system(fqdn=u'noncee.provisioned',
                status='Automated', lab_controller=data_setup.create_labcontroller())
        for _ in range(20):
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe], owner=cee_user)
            data_setup.mark_recipe_complete(recipe, system=noncee_provisioned_system)
        session.flush()

        rows = self.execute_reporting_query('cee/all-systems').fetchall()
        self.assertEqual(len(rows), 3)

        rows = self.execute_reporting_query('cee/reserved-systems').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].fqdn, u'gsslab.reserved')
        self.assertEqual(rows[0].start_time, datetime.datetime(2016, 1, 1, 0, 0))

        rows = self.execute_reporting_query('cee/loaned-systems').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].fqdn, u'gsslab.loaned')

        rows = self.execute_reporting_query('cee/loaned-systems-by-date').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].fqdn, u'gsslab.loaned')
        self.assertEqual(rows[0].loan_date, datetime.datetime(2016, 1, 2, 0, 0))

        rows = self.execute_reporting_query('cee/system-provisions').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].fqdn, u'gsslab.provisioned')
        self.assertEqual(rows[0].count, 1)

        rows = self.execute_reporting_query('cee/system-reservations').fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].fqdn, u'gsslab.provisioned')
        self.assertEqual(rows[0].count, 1)
        self.assertEqual(rows[1].fqdn, u'gsslab.reserved')
        self.assertEqual(rows[1].count, 1)

        rows = self.execute_reporting_query('cee/system-distrotrees').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].fqdn, u'gsslab.provisioned')
        self.assertEqual(rows[0].operatingsystem, u'RHEL-7.1 Server i386')

        rows = self.execute_reporting_query('cee/provisions-by-distrotree').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].operatingsystem, u'RHEL-7.1 Server i386')
        self.assertEqual(rows[0].count, 1)

        rows = self.execute_reporting_query('cee/provisions-by-user').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].user_name, u'billybob')
        self.assertEqual(rows[0].count, 21)

        rows = self.execute_reporting_query('cee/non-cee-provisions-by-user').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].fqdn, u'noncee.provisioned')
        self.assertEqual(rows[0].count, 20)
