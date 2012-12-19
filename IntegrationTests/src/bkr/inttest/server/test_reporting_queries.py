
import unittest
import pkg_resources
import datetime
from decimal import Decimal
from turbogears.database import session
from bkr.server import model
from bkr.server.model import System, RecipeTask, Cpu, SystemStatus, SystemActivity
from bkr.inttest import data_setup, DummyVirtManager

class ReportingQueryTest(unittest.TestCase):

    def setUp(self):
        self.orig_VirtManager = model.VirtManager
        model.VirtManager = DummyVirtManager
        session.begin()

    def tearDown(self):
        model.VirtManager = self.orig_VirtManager
        session.rollback()

    def execute_reporting_query(self, name):
        sql = pkg_resources.resource_string('bkr.server', 'reporting-queries/%s.sql' % name)
        return session.connection(System).execute(sql)

    def test_resource_install_failures(self):
        system_recipe = data_setup.create_recipe()
        guest_recipe = data_setup.create_guestrecipe(host=system_recipe)
        virt_recipe = data_setup.create_recipe()
        job = data_setup.create_job_for_recipes([guest_recipe, virt_recipe, system_recipe])

        data_setup.mark_recipe_running(virt_recipe, virt=True)
        data_setup.mark_recipe_running(system_recipe)
        data_setup.mark_recipe_running(guest_recipe)
        session.flush()

        # Test we don't count runinng recipes
        rows = self.execute_reporting_query('install-failure-count-by-resource')
        all_rows = [row for row in rows]
        guest_rows = [row for row in all_rows if row.fqdn == 'All Guest']
        virt_rows = [row for row in all_rows if row.fqdn == 'All Virt']
        system_rows = [row for row in all_rows if row.fqdn == system_recipe.resource.fqdn]

        self.assertEquals(len(virt_rows), 1, virt_rows)
        self.assertEquals(virt_rows[0].failed_recipes, 0)

        self.assertEquals(len(guest_rows), 1, guest_rows)
        self.assertEquals(guest_rows[0].failed_recipes, 0)

        self.assertEquals(len(system_rows), 1, system_rows)
        self.assertEquals(system_rows[0].failed_recipes, 0)

        # Test completed recipes
        data_setup.mark_job_complete(job, only=True)
        session.flush()
        rows = self.execute_reporting_query('install-failure-count-by-resource')
        all_rows = [row for row in rows]
        guest_rows = [row for row in all_rows if row.fqdn == 'All Guest']
        virt_rows = [row for row in all_rows if row.fqdn == 'All Virt']
        system_rows = [row for row in all_rows if row.fqdn == system_recipe.resource.fqdn]

        self.assertEquals(len(virt_rows), 1, virt_rows)
        self.assertEquals(virt_rows[0].failed_recipes, 1)

        self.assertEquals(len(guest_rows), 1, guest_rows)
        self.assertEquals(guest_rows[0].failed_recipes, 1)

        self.assertEquals(len(system_rows), 1, system_rows)
        self.assertEquals(system_rows[0].failed_recipes, 1)

    # https://bugzilla.redhat.com/show_bug.cgi?id=877264
    def test_machine_hours(self):
        user = data_setup.create_user()
        data_setup.create_completed_job(owner=user,
                distro_tree=data_setup.create_distro_tree(arch=u'ia64'),
                start_time=datetime.datetime(2012, 12, 16, 0, 0, 0),
                finish_time=datetime.datetime(2012, 12, 16, 1, 30, 0))
        data_setup.create_completed_job(owner=user,
                distro_tree=data_setup.create_distro_tree(arch=u'ppc64'),
                start_time=datetime.datetime(2012, 12, 16, 0, 0, 0),
                finish_time=datetime.datetime(2012, 12, 16, 2, 0, 0))
        session.flush()
        rows = self.execute_reporting_query('machine-hours-by-arch-user-month')
        user_rows = [row for row in rows if row.username == user.user_name]
        self.assertEquals(len(user_rows), 2, user_rows)
        self.assertEquals(user_rows[0].year_month, 201212)
        self.assertEquals(user_rows[0].arch, 'ia64')
        self.assertEquals(user_rows[0].machine_hours, Decimal('1.5'))
        self.assertEquals(user_rows[1].year_month, 201212)
        self.assertEquals(user_rows[1].arch, 'ppc64')
        self.assertEquals(user_rows[1].machine_hours, Decimal('2.0'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=877272
    def test_task_durations(self):
        short_task = data_setup.create_task()
        long_task = data_setup.create_task()
        r = data_setup.create_recipe()
        r.tasks[:] = [RecipeTask(task=short_task), RecipeTask(task=long_task)]
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
                datetime.datetime.utcnow() - datetime.timedelta(days=100))
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
