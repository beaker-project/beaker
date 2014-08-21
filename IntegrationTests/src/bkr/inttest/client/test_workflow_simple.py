
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import unittest2 as unittest
import pkg_resources
import re
import textwrap
from threading import Thread
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, start_client, \
    create_client_config, ClientError
from bkr.server.model import Job, Arch

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
            self.assertTrue('User %s is not a member of group %s' % \
                (user_not_in_group.user_name, group.group_name) in \
                e.stderr_output, e)

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

    def test_clean_defaults(self):
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        # Try to minimise noise in the default output
        self.assertNotIn('ks_appends', out)

    def test_hostrequire(self):
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--hostrequire', 'hostlabcontroller=lab.example.com',
                '--systype', 'machine',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assertIn('<hostlabcontroller op="=" value="lab.example.com"/>', out)
        self.assertIn('<system_type op="=" value="machine"/>', out)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1081390
    def test_hostfilter_preset(self):
        out = run_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--host-filter', "INTEL__FAM15_CELERON",
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name])
        self.assertIn('<model_name op="like" value="%Celeron%"/>', out)

        # with other host requires
        out = run_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--host-filter', "INTEL__FAM15_CELERON",
                          '--hostrequire', 'hostlabcontroller=lab.example.com',
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name])
        self.assertIn('<model_name op="like" value="%Celeron%"/>', out)
        self.assertIn('<hostlabcontroller op="=" value="lab.example.com"/>', out)

        # Override $HOME and check if the updated defintion is read
        test_home = pkg_resources.resource_filename \
                    ('bkr.inttest.client', '.')
        out = run_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--host-filter', "INTEL__FAM15_CELERON",
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name], 
                         extra_env={'HOME':test_home})
        self.assertIn('<model_name op="like" value="%MyCeleron%"/>', out)

        # Non-existent filter
        try:
            run_client(['bkr', 'workflow-simple',
                        '--dryrun', '--prettyxml',
                        '--host-filter', "awesomefilter",
                        '--arch', self.distro_tree.arch.arch,
                        '--family', self.distro.osversion.osmajor.osmajor,
                        '--task', self.task.name])
            self.fail('Must fail or die')
        except ClientError as e:
            self.assertIn('Pre-defined host-filter does not exist: awesomefilter', e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1014693
    def test_hostrequire_raw_xml(self):
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--hostrequire', '<device vendor_id="8086"/>',
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assertIn('<device vendor_id="8086"/>', out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1095026
    def test_machine_ignore_other_options(self):
        p = start_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--hostrequire', 'hostlabcontroller=lab.example.com',
                          '--random',
                          '--host-filter', 'my_awesome_filter',
                          '--machine', 'test.system',
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name])

        out, err = p.communicate()
        self.assertEquals(p.returncode, 0, err)
        self.assertIn('Warning: Ignoring --hostrequire because '
                      '--machine was specified', err.split('\n'))
        self.assertIn('Warning: Ignoring --random because '
                      '--machine was specified', err.split('\n'))
        self.assertIn('Warning: Ignoring --host-filter because '
                      '--machine was specified', err.split('\n'))
        self.assertNotIn('<hostlabcontroller op="=" value="lab.example.com"/>',
                         out)
        self.assertNotIn('<autopick random="true"/>', out)
        self.assertIn('<hostname op="=" value="test.system"/>',
                      out)


    def test_repo(self):
        first_url = 'http://repo1.example.invalid'
        second_url = 'ftp://repo2.example.invalid'
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--repo', first_url,
                '--repo', second_url,
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        expected_snippet = '<repo name="myrepo_%(idx)s" url="%(repoloc)s"/>'
        first_repo = expected_snippet % dict(idx=0, repoloc=first_url)
        self.assertIn(first_repo, out)
        second_repo = expected_snippet % dict(idx=1, repoloc=second_url)
        self.assertIn(second_repo, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=867087
    def test_repopost(self):
        first_url = 'http://repo1.example.invalid'
        second_url = 'ftp://repo2.example.invalid'
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--repo-post', first_url,
                '--repo-post', second_url,
                '--arch', self.distro_tree.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        expected_snippet = textwrap.dedent('''\
            cat << EOF >/etc/yum.repos.d/beaker-postrepo%(idx)s.repo
            [beaker-postrepo%(idx)s]
            name=beaker-postrepo%(idx)s
            baseurl=%(repoloc)s
            enabled=1
            gpgcheck=0
            skip_if_unavailable=1
            EOF
            ''')
        first_repo = expected_snippet % dict(idx=0, repoloc=first_url)
        self.assertIn(first_repo, out)
        second_repo = expected_snippet % dict(idx=1, repoloc=second_url)
        self.assertIn(second_repo, out)
        # Also check these *aren't* included as install time repos
        install_repo_url_attribute = 'url="%s"'
        self.assertNotIn(install_repo_url_attribute % first_url, out)
        self.assertNotIn(install_repo_url_attribute % second_url, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=972417
    def test_servers_default_zero(self):
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                '--task', '/distribution/reservesys',
                '--clients', '2'])
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(len(job.recipesets), 1)
            self.assertEquals(len(job.recipesets[0].recipes), 2)
            self.assertEquals(job.recipesets[0].recipes[0].tasks[1].role, 'CLIENTS')
            self.assertEquals(job.recipesets[0].recipes[1].tasks[1].role, 'CLIENTS')

    # https://bugzilla.redhat.com/show_bug.cgi?id=972417
    def test_clients_default_zero(self):
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                '--task', '/distribution/reservesys',
                '--servers', '2'])
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(len(job.recipesets), 1)
            self.assertEquals(len(job.recipesets[0].recipes), 2)
            self.assertEquals(job.recipesets[0].recipes[0].tasks[1].role, 'SERVERS')
            self.assertEquals(job.recipesets[0].recipes[1].tasks[1].role, 'SERVERS')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1078941
    def test_lookup_arches_by_family(self):
        # When a family is given but no arches, the workflow commands are 
        # supposed to look up all applicable arches and create a recipe set for 
        # each one.
        with session.begin():
            distro = data_setup.create_distro(osmajor=u'DansAwesomeLinux7',
                    tags=[u'STABLE'])
            data_setup.create_distro_tree(distro=distro, arch=u'x86_64')
            data_setup.create_distro_tree(distro=distro, arch=u's390x')
        out = run_client(['bkr', 'workflow-simple',
                '--family', distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(len(job.recipesets), 2)
            self.assertEquals(job.recipesets[0].recipes[0].distro_tree.arch,
                    Arch.by_name(u'x86_64'))
            self.assertEquals(job.recipesets[1].recipes[0].distro_tree.arch,
                    Arch.by_name(u's390x'))
