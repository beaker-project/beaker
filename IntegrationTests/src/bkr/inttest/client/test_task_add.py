
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class TaskAddTest(unittest.TestCase):

    def test_add_invalid_task(self):
        try:
            run_client(['bkr', 'task-add', '/dev/null'])
            fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assert_('error reading package header' in e.stderr_output,
                    e.stderr_output)
