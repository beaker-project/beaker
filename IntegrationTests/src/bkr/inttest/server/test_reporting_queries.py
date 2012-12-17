
import unittest
import pkg_resources
import datetime
from decimal import Decimal
from turbogears.database import session
from bkr.server.model import System
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
