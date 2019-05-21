
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import start_client, run_client, ClientError, \
        ClientTestCase

class JobWatchTest(ClientTestCase):

    def test_watch_job(self):
        with session.begin():
            job = data_setup.create_job(whiteboard=u'jobwb')
        p = start_client(['bkr', 'job-watch', job.t_id])
        self.assertEquals(p.stdout.readline(),
                'Watching tasks (this may be safely interrupted)...\n')
        self.assertEquals(p.stdout.readline(), '%s jobwb: New\n' % job.t_id)
        self.assertEquals(p.stdout.readline(), '--> New: 1 [total: 1]\n')
        with session.begin():
            data_setup.mark_job_complete(job)
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0, err)
        self.assertEquals(out,
                '%s jobwb: New -> Completed\n'
                '--> Completed: 1 [total: 1]\n' % job.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1066269
    def test_watch_recipe(self):
        with session.begin():
            job = data_setup.create_job(recipe_whiteboard=u'recipewb')
            recipe = job.recipesets[0].recipes[0]
        p = start_client(['bkr', 'job-watch', recipe.t_id])
        self.assertEquals(p.stdout.readline(),
                'Watching tasks (this may be safely interrupted)...\n')
        self.assertEquals(p.stdout.readline(), '%s recipewb: New\n' % recipe.t_id)
        self.assertEquals(p.stdout.readline(), '--> New: 1 [total: 1]\n')
        with session.begin():
            data_setup.mark_job_complete(job)
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0, err)
        self.assertEquals(out,
                '%s recipewb: New -> Completed (%s)\n'
                '--> Completed: 1 [total: 1]\n'
                % (recipe.t_id, recipe.resource.fqdn))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1066269
    def test_watch_recipetask(self):
        with session.begin():
            job = data_setup.create_job()
            recipetask = job.recipesets[0].recipes[0].tasks[0]
        p = start_client(['bkr', 'job-watch', recipetask.t_id])
        self.assertEquals(p.stdout.readline(),
                'Watching tasks (this may be safely interrupted)...\n')
        self.assertEquals(p.stdout.readline(),
                '%s /distribution/reservesys: New\n' % recipetask.t_id)
        self.assertEquals(p.stdout.readline(), '--> New: 1 [total: 1]\n')
        with session.begin():
            data_setup.mark_job_complete(job)
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0, err)
        self.assertEquals(out,
                '%s /distribution/reservesys: New -> Completed (%s)\n'
                '--> Completed: 1 [total: 1]\n'
                % (recipetask.t_id, recipetask.recipe.resource.fqdn))

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-watch', '12345'])
            self.fail('should raise')
        except ClientError as e:
            self.assert_('Invalid taskspec' in e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1415104
    def test_exits_141_when_pipe_is_closed(self):
        with session.begin():
            job = data_setup.create_job(whiteboard=u'jobwb')
        p = start_client(['bkr', 'job-watch', job.t_id])
        self.assertEquals(p.stdout.readline(),
                'Watching tasks (this may be safely interrupted)...\n')
        p.stdout.close()
        err = p.stderr.read()
        p.wait()
        self.assertEquals(p.returncode, 141, err)
