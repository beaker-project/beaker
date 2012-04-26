
import unittest
import datetime
from turbogears.database import session
from bkr.server.model import SystemStatus, SystemStatusDuration
from bkr.server.utilisation import system_utilisation
from bkr.inttest import data_setup

class SystemUtilisationTest(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.commit()

    def test_durations(self):
        system = data_setup.create_system()

        # Set up the following fake history for the system:
        #   2009-12-31 00:00:00 marked broken
        #   2010-01-02 00:00:00 repaired
        #   2010-01-03 00:00:00 to 12:00:00 manually reserved
        #   2010-01-04 12:00:00 to 00:00:00 running a recipe
        system.date_added = datetime.datetime(2009, 1, 1, 0, 0, 0)
        system.status_durations.append(SystemStatusDuration(
                status=SystemStatus.broken,
                start_time=datetime.datetime(2009, 12, 31, 0, 0, 0),
                finish_time=datetime.datetime(2010, 1, 2, 0, 0, 0)))
        system.status_durations.append(SystemStatusDuration(
                status=SystemStatus.automated,
                start_time=datetime.datetime(2010, 1, 2, 0, 0, 0)))
        data_setup.create_manual_reservation(system,
                start=datetime.datetime(2010, 1, 3, 0, 0, 0),
                finish=datetime.datetime(2010, 1, 3, 12, 0, 0))
        data_setup.create_completed_job(system=system,
                start_time=datetime.datetime(2010, 1, 4, 12, 0, 0),
                finish_time=datetime.datetime(2010, 1, 5, 0, 0, 0))
        session.flush()

        # If we report from 2010-01-01 to 2010-01-04, that should give us the 
        # following durations:
        u = system_utilisation(system, datetime.datetime(2010, 1, 1, 0, 0, 0),
                datetime.datetime(2010, 1, 5, 0, 0, 0))
        self.assertEqual(u['recipe'], datetime.timedelta(seconds=43200))
        self.assertEqual(u['manual'], datetime.timedelta(seconds=43200))
        self.assertEqual(u['idle_manual'], datetime.timedelta(0))
        self.assertEqual(u['idle_automated'], datetime.timedelta(days=2))
        self.assertEqual(u['idle_broken'], datetime.timedelta(days=1))
        self.assertEqual(u['idle_removed'], datetime.timedelta(0))
        self.assertEqual(sum((v for k, v in u.iteritems()), datetime.timedelta(0)),
                datetime.timedelta(days=4))

    def test_idle_with_status_duration_covering_entire_period(self):
        system = data_setup.create_system()
        system.date_added = datetime.datetime(2009, 1, 1, 0, 0, 0)
        system.status_durations.append(SystemStatusDuration(
                status=SystemStatus.automated,
                start_time=datetime.datetime(2009, 1, 1, 0, 0, 0)))
        session.flush()

        u = system_utilisation(system, datetime.datetime(2010, 1, 1, 0, 0, 0),
                datetime.datetime(2010, 1, 5, 0, 0, 0))
        self.assertEqual(u['idle_automated'], datetime.timedelta(days=4))

    def test_system_added_during_period(self):
        system = data_setup.create_system()
        system.date_added = datetime.datetime(2010, 1, 3, 0, 0, 0)
        system.status_durations.append(SystemStatusDuration(
                status=SystemStatus.automated,
                start_time=datetime.datetime(2010, 1, 3, 0, 0, 0)))
        session.flush()

        u = system_utilisation(system, datetime.datetime(2010, 1, 1, 0, 0, 0),
                datetime.datetime(2010, 1, 5, 0, 0, 0))
        self.assertEqual(u['idle_automated'], datetime.timedelta(days=2))
        self.assertEqual(sum((v for k, v in u.iteritems()), datetime.timedelta(0)),
                datetime.timedelta(days=2))

    def test_system_removed_during_period(self):
        system = data_setup.create_system()
        system.date_added = datetime.datetime(2009, 1, 1, 0, 0, 0)
        system.status_durations.append(SystemStatusDuration(
                status=SystemStatus.automated,
                start_time=datetime.datetime(2009, 1, 1, 0, 0, 0),
                finish_time=datetime.datetime(2010, 1, 3, 0, 0, 0)))
        system.status_durations.append(SystemStatusDuration(
                status=SystemStatus.removed,
                start_time=datetime.datetime(2010, 1, 3, 0, 0, 0)))
        session.flush()

        u = system_utilisation(system, datetime.datetime(2010, 1, 1, 0, 0, 0),
                datetime.datetime(2010, 1, 5, 0, 0, 0))
        self.assertEqual(u['idle_automated'], datetime.timedelta(days=2))
        self.assertEqual(u['idle_removed'], datetime.timedelta(days=2))
        self.assertEqual(sum((v for k, v in u.iteritems()), datetime.timedelta(0)),
                datetime.timedelta(days=4))
