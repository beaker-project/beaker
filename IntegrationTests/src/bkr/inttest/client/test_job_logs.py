
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import unittest2 as unittest
import urlparse
import shutil
import tempfile
import pkg_resources
from bkr.server.model import session, LogRecipe, LogRecipeTask, LogRecipeTaskResult
from bkr.inttest import data_setup, Process
from bkr.inttest.client import run_client, ClientError

class JobLogsTest(unittest.TestCase):

    def setUp(self):
        # set up a directory for our dummy job logs, with an HTTP server
        self.logs_dir = tempfile.mkdtemp(prefix='beaker-client-test-job-logs')
        self.addCleanup(shutil.rmtree, self.logs_dir, ignore_errors=True)
        self.archive_server = Process('http_server.py', args=[sys.executable,
                pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                '--base', self.logs_dir], listen_port=19998)
        self.archive_server.start()
        self.addCleanup(self.archive_server.stop)
        self.log_server_url = u'http://localhost:19998/'
        # job for testing
        with session.begin():
            self.job = data_setup.create_completed_job()
            recipe = self.job.recipesets[0].recipes[0]
            os.mkdir(os.path.join(self.logs_dir, 'R'))
            open(os.path.join(self.logs_dir, 'R', 'dummy.txt'), 'w').write('recipe\n')
            recipe.logs[:] = [LogRecipe(server=self.log_server_url,
                    path=u'R', filename=u'dummy.txt')]
            os.mkdir(os.path.join(self.logs_dir, 'T'))
            open(os.path.join(self.logs_dir, 'T', 'dummy.txt'), 'w').write('task\n')
            recipe.tasks[0].logs[:] = [LogRecipeTask(server=self.log_server_url,
                    path=u'T', filename=u'dummy.txt')]
            os.mkdir(os.path.join(self.logs_dir, 'TR'))
            open(os.path.join(self.logs_dir, 'TR', 'dummy.txt'), 'w').write('result\n')
            recipe.tasks[0].results[0].logs[:] = [LogRecipeTaskResult(
                    server=self.log_server_url,
                    path=u'TR', filename=u'dummy.txt')]

    def test_by_job(self):
        out = run_client(['bkr', 'job-logs', self.job.t_id])
        logs = out.splitlines()
        self.assertEquals(logs[0], self.log_server_url + u'R/dummy.txt')
        self.assertEquals(logs[1], self.log_server_url + u'T/dummy.txt')
        self.assertEquals(logs[2], self.log_server_url + u'TR/dummy.txt')

    def test_by_recipeset(self):
        out = run_client(['bkr', 'job-logs', self.job.recipesets[0].t_id])
        logs = out.splitlines()
        self.assertEquals(logs[0], self.log_server_url + u'R/dummy.txt')
        self.assertEquals(logs[1], self.log_server_url + u'T/dummy.txt')
        self.assertEquals(logs[2], self.log_server_url + u'TR/dummy.txt')

    def test_by_recipe(self):
        out = run_client(['bkr', 'job-logs',
                self.job.recipesets[0].recipes[0].t_id])
        logs = out.splitlines()
        self.assertEquals(logs[0], self.log_server_url + u'R/dummy.txt')
        self.assertEquals(logs[1], self.log_server_url + u'T/dummy.txt')
        self.assertEquals(logs[2], self.log_server_url + u'TR/dummy.txt')

    def test_by_task(self):
        out = run_client(['bkr', 'job-logs',
                self.job.recipesets[0].recipes[0].tasks[0].t_id])
        logs = out.splitlines()
        self.assertEquals(logs[0], self.log_server_url + u'T/dummy.txt')
        self.assertEquals(logs[1], self.log_server_url + u'TR/dummy.txt')

    def test_by_taskresult(self):
        out = run_client(['bkr', 'job-logs',
                self.job.recipesets[0].recipes[0].tasks[0].results[0].t_id])
        logs = out.splitlines()
        self.assertEquals(logs[0], self.log_server_url + u'TR/dummy.txt')

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-logs', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)

    def test_prints_sizes(self):
        out = run_client(['bkr', 'job-logs', '--size', self.job.t_id])
        lines = out.splitlines()
        self.assertEquals(lines[0], '     7 %sR/dummy.txt' % self.log_server_url)
        self.assertEquals(lines[1], '     5 %sT/dummy.txt' % self.log_server_url)
        self.assertEquals(lines[2], '     7 %sTR/dummy.txt' % self.log_server_url)

    def test_size_handles_404(self):
        with session.begin():
            self.job.recipesets[0].recipes[0].logs[0].filename = u'idontexist.txt'
        out = run_client(['bkr', 'job-logs', '--size', self.job.t_id])
        lines = out.splitlines()
        self.assertEquals(lines[0], '<missing> %sR/idontexist.txt' % self.log_server_url)

    def test_size_handles_http_errors(self):
        with session.begin():
            # /error/500 is treated specially by http_server.py, returns 500
            self.job.recipesets[0].recipes[0].logs[0].path = u'error'
            self.job.recipesets[0].recipes[0].logs[0].filename = u'500'
        out = run_client(['bkr', 'job-logs', '--size', self.job.t_id])
        lines = out.splitlines()
        self.assertEquals(lines[0], '<error:500> %serror/500' % self.log_server_url)
