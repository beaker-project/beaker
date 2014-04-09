
# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest2 as unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, ClientError

class JobResultsTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_completed_job()

    def test_by_job(self):
        out = run_client(['bkr', 'job-results', self.job.t_id])
        self.assert_(out.startswith('<job '))

    def test_by_recipeset(self):
        out = run_client(['bkr', 'job-results', self.job.recipesets[0].t_id])
        self.assert_(out.startswith('<recipeSet '))

    def test_by_recipe(self):
        out = run_client(['bkr', 'job-results',
                self.job.recipesets[0].recipes[0].t_id])
        self.assert_(out.startswith('<recipe '))

    def test_by_recipetask(self):
        out = run_client(['bkr', 'job-results',
                self.job.recipesets[0].recipes[0].tasks[0].t_id])
        self.assert_(out.startswith('<task '))

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-results', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1014623
    def test_nonascii_chars_in_job_xml(self):
        with session.begin():
            job = data_setup.create_completed_job(
                    whiteboard=u'Фёдор Михайлович Достоевский')
        out = run_client(['bkr', 'job-results', job.t_id])
        self.assertIn(job.whiteboard, out.decode('utf8'))
        out = run_client(['bkr', 'job-results', '--prettyxml', job.t_id])
        self.assertIn(job.whiteboard, out.decode('utf8'))
