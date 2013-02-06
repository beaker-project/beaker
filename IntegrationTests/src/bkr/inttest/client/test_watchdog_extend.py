import unittest
from bkr.inttest.client import run_client, ClientError

class WatchdogExtend(unittest.TestCase):

    def test_watchdog_extend(self):

        try:
            out = run_client(['bkr','watchdog-extend'])
        except ClientError, e:
            self.assert_('Please specify one or more task ids.' in e.stderr_output)

        try:
            out = run_client(['bkr','watchdog-extend', '0000'])
        except ClientError, e:
            self.assert_('Invalid task ID: 0000' in e.stderr_output)


