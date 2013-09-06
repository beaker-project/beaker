
import unittest
import subprocess
import signal
from gevent.hub import LoopExit
from bkr.labcontroller.async import MonitoredSubprocess

class SubprocessTest(unittest.TestCase):

    def test_runaway_output_is_discarded(self):
        p = MonitoredSubprocess(['seq', '--format=%0.0f cans of spam on the wall',
                str(1024 * 1024)], stdout=subprocess.PIPE)
        try:
            p.dead.wait()
        except LoopExit:
            pass # Already terminated
        out = p.stdout_reader.get()
        self.assert_(len(out) <= 4096013, len(out))
        self.assert_(out.endswith('+++ DISCARDED'), out[:-10240])

    def test_timeout_is_enforced(self):
        p = MonitoredSubprocess(['sleep', '10'], timeout=1)
        p.dead.wait()
        self.assertEquals(p.returncode, -signal.SIGTERM)

    # https://bugzilla.redhat.com/show_bug.cgi?id=832250
    def test_reaper_race(self):
        procs = [MonitoredSubprocess(['true'], timeout=10)
                for _ in xrange(800)]
        for p in procs:
            p.dead.wait()
