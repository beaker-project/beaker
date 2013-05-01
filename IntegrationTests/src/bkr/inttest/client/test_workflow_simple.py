import os
import unittest
import subprocess
import re
from threading import Thread
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, start_client, \
    create_client_config, ClientError
from bkr.server.model import Job

class WorkflowSimpleTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro(tags=[u'STABLE'])
        self.distro_tree = data_setup.create_distro_tree(distro=self.distro)
        self.task = data_setup.create_task()

    def test_job_group(self):
        with session.begin():
            user_in_group = data_setup.create_user(password='password')
            group = data_setup.create_group()
            user_in_group.groups.append(group)
            user_not_in_group = data_setup.create_user(password='password')

        # Test submitting on behalf of user's group
        config1 = create_client_config(username=user_in_group.user_name,
            password='password')
        out = run_client(['bkr', 'workflow-simple', '--random',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--job-group', group.group_name,
                '--task', self.task.name], config=config1)
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
        self.assertEqual(group, job.group)

        # Test submitting on behalf of group user does not belong to
        config2 = create_client_config(username=user_not_in_group.user_name,
            password='password')
        try:
            out2 = run_client(['bkr', 'workflow-simple', '--random',
                    '--arch', self.distro_tree.arch.arch,
                    '--family', self.distro.osversion.osmajor.osmajor,
                    '--job-group', group.group_name,
                    '--task', self.task.name], config=config2)
            fail('should raise')
        except ClientError, e:
            self.assertTrue('You are not a member of the %s group' % \
                group.group_name in e.stderr_output, e)

    def test_submit_job(self):
        out = run_client(['bkr', 'workflow-simple', '--random',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assert_(out.startswith('Submitted:'), out)

    def test_submit_job_wait(self):
        args = ['bkr', 'workflow-simple', '--random',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name,
                '--wait']
        proc = start_client(args)
        out = proc.stdout.readline().rstrip()
        self.assert_(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)

        out = proc.stdout.readline().rstrip()
        self.assert_('Watching tasks (this may be safely interrupted)...' == out)

        with session.begin():
            job = Job.by_id(job_id)
            job.cancel()
            job.update_status()

        returncode = proc.wait()
        self.assert_(returncode == 1)

    def test_hostrequire(self):
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--hostrequire', 'hostlabcontroller=lab.example.com',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assert_('<hostlabcontroller op="=" value="lab.example.com"/>' in out, out)
