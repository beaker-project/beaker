
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from threading import Thread, Event
from turbogears.database import session
from bkr.server.model import System, SystemStatus
from bkr.inttest import data_setup, DatabaseTestCase

log = logging.getLogger(__name__)

class SystemStatusTest(DatabaseTestCase):

    def check_status_durations(self, system):
        # The crucial invariant is that there is exactly one row with NULL 
        # finish_time.
        self.assert_(len([sd for sd in system.status_durations if sd.finish_time is None])
                == 1, system.status_durations)

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
