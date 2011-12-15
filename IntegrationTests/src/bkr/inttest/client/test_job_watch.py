
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import start_client
import time
from nose.plugins.skip import SkipTest

class JobWatchTest(unittest.TestCase):

    def test_watch_job(self):
        raise SkipTest('too slow (>30 sec)')
        job = data_setup.create_job()
        session.flush()
        p = start_client(['bkr', 'job-watch', job.t_id])
        time.sleep(1) # XXX better would be to read the client's stdout
        data_setup.mark_job_complete(job)
        session.flush()
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assert_(out.startswith('Watching tasks'), out)
        self.assert_('New: 1 [total: 1]' in out, out)
        self.assert_('Completed: 1 [total: 1]' in out, out)
