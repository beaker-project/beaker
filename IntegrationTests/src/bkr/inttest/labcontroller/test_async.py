
import unittest
import subprocess
import signal
from bkr.labcontroller.async import MonitoredSubprocess

class SubprocessTest(unittest.TestCase):

    def test_runaway_output_is_discarded(self):
        p = MonitoredSubprocess(['seq', '--format=%0.0f cans of spam on the wall',
                str(1024 * 1024)], stdout=subprocess.PIPE)
        p.dead.wait()
        out = p.stdout_reader.get()
        self.assert_(len(out) <= 4096013, len(out))
        self.assert_(out.endswith('+++ DISCARDED'), out[:-10240])

    def test_timeout_is_enforced(self):
        p = MonitoredSubprocess(['sleep', '10'], timeout=1)
        p.dead.wait()
        self.assertEquals(p.returncode, -signal.SIGTERM)
