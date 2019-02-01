
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from threading import Thread, Event
from turbogears.database import session
from bkr.server.model import System, SystemStatus, CommandStatus
from bkr.inttest import data_setup, DatabaseTestCase

log = logging.getLogger(__name__)

class SystemStatusTest(DatabaseTestCase):

    def assert_commands_in_same_state(self, system, required_status):
        """
        Asserts that all commands in the system's command
        queue are in the same state
        :param system: System to to check
        :param required_status: Status to assert
        """
        states = set([c.status for c in system.command_queue])
        self.assertEqual(1, len(states), "Commands in more than one state")
        self.assertIn(required_status, states)

    def check_status_durations(self, system):
        # The crucial invariant is that there is exactly one row with NULL
        # finish_time.
        self.assert_(len([sd for sd in system.status_durations if sd.finish_time is None])
                == 1, system.status_durations)

    def setup_system_with_queued_commands(self):
        with session.begin():
            system = data_setup.create_system(status=u'Automated',
                                              lab_controller=data_setup.create_labcontroller())
            system.action_power(action='clear_logs')
            system.action_power(action='configure_netboot')
            system.action_power(action='reboot')
        session.flush()

        self.assertEqual(4, len(system.command_queue))
        self.assert_commands_in_same_state(system, CommandStatus.queued)
        return system

    # https://bugzilla.redhat.com/show_bug.cgi?id=903902
    def test_concurrent_updates(self):
        # This bug was originally caused by beaker-provision running the same 
        # command twice concurrently, which would typically cause them both to 
        # report failure at the exact same moment. As a result, we had two 
        # concurrent transactions marking the same system as broken.
        # This test just touches the model objects directly, so that we can 
        # use threads to guarantee concurrent transactions.
        with session.begin():
            system = data_setup.create_system(status=u'Automated')
            self.check_status_durations(system)

        class MarkBrokenThread(Thread):
            def __init__(self, **kwargs):
                super(MarkBrokenThread, self).__init__(**kwargs)
                self.ready_evt = Event()
                self.continue_evt = Event()
            def run(self):
                try:
                    session.begin()
                    system_local = System.query.get(system.id)
                    assert system_local.status == SystemStatus.automated
                    self.ready_evt.set()
                    self.continue_evt.wait()
                    system_local.mark_broken(reason=u'Murphy', service=u'testdata')
                    session.commit()
                except:
                    # We expect one thread to get an exception, don't care which one though.
                    # Catching it here just prevents it spewing onto stderr.
                    log.exception('Exception in MarkBrokenThread (one is expected)')

        thread1 = MarkBrokenThread()
        thread2 = MarkBrokenThread()
        thread1.start()
        thread2.start()
        thread1.ready_evt.wait()
        thread2.ready_evt.wait()
        thread1.continue_evt.set()
        thread2.continue_evt.set()
        thread1.join()
        thread2.join()

        with session.begin():
            session.expire_all()
            self.assertEquals(system.status, SystemStatus.broken)
            self.check_status_durations(system)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1362371
    def test_queued_commands_aborted_when_system_removed(self):
        system = self.setup_system_with_queued_commands()
        system.status = SystemStatus.removed
        self.assert_commands_in_same_state(system, CommandStatus.aborted)

    # https: // bugzilla.redhat.com / show_bug.cgi?id = 1362371
    def test_queued_commands_aborted_when_lab_controller_removed(self):
        system = self.setup_system_with_queued_commands()
        system.lab_controller = None
        self.assert_commands_in_same_state(system, CommandStatus.aborted)
        for c in system.command_queue:
            self.assertEqual(u"System disassociated from lab controller", c.error_message)