
import unittest
import pkg_resources
import datetime
from decimal import Decimal
from turbogears.database import session
from bkr.server.model import System, RecipeTask
from bkr.inttest import data_setup

class ReportingQueryTest(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def execute_reporting_query(self, name):
        sql = pkg_resources.resource_string('bkr.server', 'reporting-queries/%s.sql' % name)
        return session.connection(System).execute(sql)

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
