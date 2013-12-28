
import os
import errno
import unittest2 as unittest
import subprocess
import signal
from time import sleep
import gevent
try:
    from gevent import wait as gevent_wait
except ImportError:
    # gevent.wait was gevent.run in 1.0 beta
    from gevent import run as gevent_wait
from bkr.labcontroller.async import MonitoredSubprocess

class SubprocessTest(unittest.TestCase):

    def _assert_child_is_process_group_leader(self, p):
        self.assertEqual(os.getpgid(p.pid), p.pid)

    def _assert_process_group_is_removed(self, pgid):
        try:
            # There's seems to sometimes be a delay from when the process is killed
            # and when os.killpg believes it is killed
            for _ in range(1,6):
                os.killpg(pgid, signal.SIGKILL)
                sleep(0.5)
            self.fail("The process group should've already been removed")
        except OSError, e:
            if e.errno != errno.ESRCH:
                self.fail("The process group should've already been removed")

    def test_runaway_output_is_discarded(self):
        def _test():
            p = MonitoredSubprocess(['seq', '--format=%0.0f cans of spam on the wall',
                    str(1024 * 1024)], stdout=subprocess.PIPE)
            p.dead.wait()
            out = p.stdout_reader.get()
            self.assert_(len(out) <= 4096013, len(out))
            self.assert_(out.endswith('+++ DISCARDED'), out[:-10240])
        gevent.spawn(_test)
        gevent_wait()

    def test_timeout_is_enforced(self):
        def _test():
            p = MonitoredSubprocess(['sleep', '10'], timeout=1)
            p.dead.wait()
            self.assertEquals(p.returncode, -signal.SIGTERM)
        gevent.spawn(_test)
        gevent_wait()

    def test_child_is_process_group_leader(self):
        def _test():
            p = MonitoredSubprocess(['sleep', '1'])
            self._assert_child_is_process_group_leader(p)
            p.dead.wait()
        gevent.spawn(_test)
        gevent_wait()

    def test_process_group_is_killed_on_leader_timeout(self):
        # This test makes the following process tree:
        #
        #           MonitoredSubprocess
        #                  |
        #                  |
        #                 bash
        #                 /  \
        #                /    \
        #               /      \
        #           sleep 10   bash
        #                        |
        #                        |
        #                     sleep 30
        #
        # The process group leader should timeout, and everything in the
        # process group should be terminated/killed.
        def _test():
            p = MonitoredSubprocess(['bash', '-c', '{ sleep 30 ; } & sleep 10'], timeout=1)
            # The rest of this test hinges on this assertion
            self._assert_child_is_process_group_leader(p)
            p.dead.wait()
            self.assertIn(p.returncode, [-signal.SIGTERM, -signal.SIGKILL])
            self._assert_process_group_is_removed(p.pid)
        gevent.spawn(_test)
        gevent_wait()

    def test_orphan_child_is_killed_when_parent_exits(self):
        # This test makes the following process tree:
        #
        #           MonitoredSubprocess
        #                  |
        #                  |
        #                 bash
        #                 /  \
        #                /    \
        #               /      \
        #           sleep 1    bash
        #                        |
        #                        |
        #                     sleep 60
        #
        # These should all be in the same process group and should
        # all be killed when the process group leader exits normally.
        def _test():
            p = MonitoredSubprocess(['bash', '-c', '{ sleep 60 ; } & sleep 1'], timeout=10)
            # The rest of this test hinges on this assertion
            self._assert_child_is_process_group_leader(p)
            p.dead.wait()
            self.assertEquals(p.returncode, 0)
            self._assert_process_group_is_removed(p.pid)
        gevent.spawn(_test)
        gevent_wait()

    # https://bugzilla.redhat.com/show_bug.cgi?id=832250
    def test_reaper_race(self):
        def _test():
            procs = [MonitoredSubprocess(['true'], timeout=10)
                    for _ in xrange(800)]
            for p in procs:
                p.dead.wait()
        gevent.spawn(_test)
        gevent_wait()
