
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import start_client, run_client, ClientError
import time
from nose.plugins.skip import SkipTest

class JobWatchTest(unittest.TestCase):

    def test_watch_job(self):
        with session.begin():
            job = data_setup.create_job()
        p = start_client(['bkr', 'job-watch', job.t_id])
        time.sleep(1) # XXX better would be to read the client's stdout
        with session.begin():
            data_setup.mark_job_complete(job)
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0, err)
        self.assert_(out.startswith('Watching tasks'), out)
        self.assert_('New: 1 [total: 1]' in out, out)
        self.assert_('Completed: 1 [total: 1]' in out, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-watch', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)
