# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import re
import textwrap
from tempfile import NamedTemporaryFile
import pkg_resources
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, start_client, \
    create_client_config, ClientError, ClientTestCase
from bkr.server.model import Job, SystemStatus


class WorkflowSimpleTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro(tags=[u'STABLE'])
        self.distro_tree = data_setup.create_distro_tree(distro=self.distro)
        # multihost task required as bkr assumes there is always one available
        self.multihost_task = data_setup.create_task(type=[u'Multihost'])
        self.task = data_setup.create_task(runfor=[u'apache'])

    def test_no_specified_tasks_throws_relevant_error_with_hint(self):
        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'workflow-simple',
                        '--dryrun', '--prettyxml',
                        '--arch', self.distro_tree.arch.arch,
                        '--family', self.distro.osversion.osmajor.osmajor])
        self.assertIn(
            'No tasks specified to be run\nHint', assertion.exception.stderr_output)

    def test_package_option_without_assocaited_tasks_throws_error(self):
        # package with associated task runs error-free
        out = run_client(['bkr', 'workflow-simple',
                          '--package', "apache",
                          '--family', self.distro.osversion.osmajor.osmajor])
        self.assertIn('Submitted', out)

        # package without associated task throws error
        with self.assertRaises(ClientError) as assertion:
            run_client(['bkr', 'workflow-simple',
                        '--package', "nonexistentpackage",
                        '--family', self.distro.osversion.osmajor.osmajor])
        self.assertIn(
            'No tasks match the specified option(s)', assertion.exception.stderr_output)

    def test_job_group(self):
        with session.begin():
            user_in_group = data_setup.create_user(password='password')
            group = data_setup.create_group()
            group.add_member(user_in_group)
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
            run_client(['bkr', 'workflow-simple', '--random',
                        '--arch', self.distro_tree.arch.arch,
                        '--family', self.distro.osversion.osmajor.osmajor,
                        '--job-group', group.group_name,
                        '--task', self.task.name], config=config2)
            self.fail('should raise')
        except ClientError as e:
            self.assertTrue('User %s is not a member of group %s' % \
                            (user_not_in_group.user_name, group.group_name) in \
                            e.stderr_output, e)

    def test_job_owner(self):
        with session.begin():
            bot = data_setup.create_user(password='bot')
            user = data_setup.create_user()
            user.add_submission_delegate(bot, service=u'testdata')
        config = create_client_config(username=bot.user_name, password='bot')
        out = run_client(['bkr', 'workflow-simple',
                          '--job-owner', user.user_name,
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name], config=config)
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(job.owner, user)

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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1081390
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
                         extra_env={'HOME': test_home})
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=883020
    def test_hostrequire_shows_error_for_unparseable_values(self):
        with self.assertRaises(ClientError) as assertion:
            out = run_client(['bkr', 'workflow-simple',
                              '--dryrun', '--prettyxml',
                              '--hostrequire', 'asdf',
                              '--arch', self.distro_tree.arch.arch,
                              '--family', self.distro.osversion.osmajor.osmajor,
                              '--task', self.task.name])
        self.assertIn(
            '--hostrequire option must be in the form "TAG OPERATOR VALUE"',
            assertion.exception.stderr_output)

    def test_keyvalue_shows_error_for_unparseable_values(self):
        with self.assertRaises(ClientError) as assertion:
            out = run_client(['bkr', 'workflow-simple',
                              '--dryrun', '--prettyxml',
                              '--keyvalue', 'asdf',
                              '--arch', self.distro_tree.arch.arch,
                              '--family', self.distro.osversion.osmajor.osmajor,
                              '--task', self.task.name])
        self.assertIn(
            '--keyvalue option must be in the form "KEY OPERATOR VALUE"',
            assertion.exception.stderr_output)

    def test_reserve(self):
        out = run_client(['bkr', 'workflow-simple',
                          '--dry-run', '--pretty-xml',
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name,
                          '--reserve', '--reserve-duration', '3600'])
        self.assertIn('<reservesys duration="3600"/>', out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1095026
    def test_machine_ignore_other_options(self):
        p = start_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--hostrequire', 'hostlabcontroller=lab.example.com',
                          '--random',
                          '--host-filter', 'my_awesome_filter',
                          '--machine', 'test.system',
                          '--ignore-system-status',
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
        self.assertIn('<hostRequires force="test.system"/>',
                      out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1234323
    def test_accepts_machine_and_systype(self):
        out = run_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--machine', 'system.example.com',
                          '--systype', 'Prototype',
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name])
        self.assertIn('<hostname op="=" value="system.example.com"/>', out)
        self.assertIn('<system_type op="=" value="Prototype"/>', out)

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

    def submit_job_and_check_arches(self, workflow_options, expected_arches):
        out = run_client(['bkr', 'workflow-simple', '--task', self.task.name]
                         + workflow_options)
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEqual(len(job.recipesets), len(expected_arches))
            actual_arches = [rs.recipes[0].distro_tree.arch.arch for rs in job.recipesets]
            self.assertItemsEqual(actual_arches, expected_arches)

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
        self.submit_job_and_check_arches(
            ['--family', distro.osversion.osmajor.osmajor],
            [u'x86_64', u's390x'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1255420
    def test_looks_up_arches_for_suitable_osminor(self):
        # RHEL7 is the first time we have had differing arches across a single
        # OS major. We want the workflow command to use the set of arches for
        # the OS version which will actually match whatever distro filtering
        # options we are using, e.g. latest RedHatEnterpriseLinux7 should be
        # using RHEL7.2 arches, not RHEL7.0.
        with session.begin():
            older_arches = [u'x86_64', u's390x']
            older_distro = data_setup.create_distro(
                osmajor=u'DansAwesomeLinux8', osminor=u'0',
                arches=older_arches,
                date_created=datetime.datetime(2010, 1, 1, 0, 0),
                tags=[u'STABLE'])
            for arch in older_arches:
                data_setup.create_distro_tree(distro=older_distro, arch=arch)
            newer_arches = [u'x86_64', u's390x', u'ppc64le']
            newer_distro = data_setup.create_distro(
                osmajor=u'DansAwesomeLinux8', osminor=u'1',
                arches=newer_arches,
                date_created=datetime.datetime(2012, 1, 1, 0, 0),
                tags=[])
            for arch in newer_arches:
                data_setup.create_distro_tree(distro=newer_distro, arch=arch)
        # Naming a specific distro should always use the corresponding OS minor arches.
        self.submit_job_and_check_arches(['--distro', older_distro.name], older_arches)
        self.submit_job_and_check_arches(['--distro', newer_distro.name], newer_arches)
        # Giving a family in addition to a specific distro is redundant, but it
        # shouldn't break the arch lookup.
        self.submit_job_and_check_arches(
            ['--distro', older_distro.name, '--family', 'DansAwesomeLinux8'],
            older_arches)
        self.submit_job_and_check_arches(
            ['--distro', newer_distro.name, '--family', 'DansAwesomeLinux8'],
            newer_arches)
        # Naming just a family will use the latest distro in that family.
        self.submit_job_and_check_arches(['--family', 'DansAwesomeLinux8'], newer_arches)
        # Family filtered by tag can restrict it to an older release though.
        self.submit_job_and_check_arches(
            ['--family', 'DansAwesomeLinux8', '--tag', 'STABLE'],
            older_arches)

    def test_kickstart_template(self):
        template_contents = 'install\n%packages\n%end\n'
        template_file = NamedTemporaryFile()
        template_file.write(template_contents)
        template_file.flush()
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                          '--task', self.task.name,
                          '--kickstart', template_file.name])
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(job.recipesets[0].recipes[0].kickstart,
                              template_contents)

    def test_kickstart_template_with_kernel_options(self):
        template_contents = """
## kernel_options: sshd=1
install
%packages
%end
        """
        template_file = NamedTemporaryFile()
        template_file.write(template_contents)
        template_file.flush()
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                          '--task', self.task.name,
                          '--kickstart', template_file.name])
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(job.recipesets[0].recipes[0].kernel_options,
                              "sshd=1")

    # https://bugzilla.redhat.com/show_bug.cgi?id=856687
    def test_ks_append(self):
        first_ks = 'append1'
        second_ks = 'append2'
        out = run_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--ks-append', first_ks,
                          '--ks-append', second_ks,
                          '--arch', self.distro_tree.arch.arch,
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--task', self.task.name])
        self.assertIn("<ks_append>\n<![CDATA[%s]]>\t\t\t\t</ks_append>" % first_ks, out)
        self.assertIn("<ks_append>\n<![CDATA[%s]]>\t\t\t\t</ks_append>" % second_ks, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220652
    def test_no_default_install_method(self):
        # Not specifying a method in ks_meta means Beaker picks one. We want
        # that to be the default behaviour if --method is not given.
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                          '--task', self.task.name])
        self.assertTrue(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEquals(job.recipesets[0].recipes[0].ks_meta, u'')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1323921
    def test_can_do_dry_run_anonymously(self):
        config = create_client_config(username=u'ignored', password=u'ignored',
                                      auth_method=u'none')
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                          '--task', self.task.name, '--dry-run', '--pretty-xml'],
                         config=config)
        self.assertIn('<job', out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1319988
    def test_ignore_system_status(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc,
                                              status=SystemStatus.broken)
        out = run_client(['bkr', 'workflow-simple', '--distro', self.distro.name,
                          '--machine', system.fqdn,
                          '--ignore-system-status',
                          '--task', self.task.name, '--dry-run', '--pretty-xml'])
        self.assertIn('<hostRequires force="%s"/>' % system.fqdn, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1197608
    def test_filters_task_by_arch_with_given_taskfile(self):
        with session.begin():
            ignored_task = data_setup.create_task(exclude_arches=[self.distro_tree.arch.arch])
            included_task = data_setup.create_task()

        taskfile = NamedTemporaryFile()
        taskfile.write('\n'.join([ignored_task.name, included_task.name]))
        taskfile.flush()

        out = run_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--arch', self.distro_tree.arch.arch,
                          '--taskfile', taskfile.name])

        self.assertNotIn(ignored_task.name, out)
        self.assertIn(included_task.name, out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1197608
    def test_filters_task_by_osmajor_with_given_taskfile(self):
        with session.begin():
            ignored_task = data_setup.create_task(
                exclude_osmajors=[self.distro.osversion.osmajor.osmajor])
            included_task = data_setup.create_task()

        taskfile = NamedTemporaryFile()
        taskfile.write('\n'.join([ignored_task.name, included_task.name]))
        taskfile.flush()

        p = start_client(['bkr', 'workflow-simple',
                          '--dryrun', '--prettyxml',
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--arch', self.distro_tree.arch.arch,
                          '--taskfile', taskfile.name])
        out, err = p.communicate()
        self.assertEqual(p.returncode, 0)
        self.assertEqual('WARNING: task %s not applicable for distro, ignoring\n' % ignored_task.name, err)
        self.assertNotIn(ignored_task.name, out)
        self.assertIn(included_task.name, out)

    def _verify_check_install(self, distro):
        out = run_client(['bkr', 'workflow-simple',
                          '--distro', distro.name,
                          '--task', self.task.name])
        self.assertIn('Submitted:', out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)
        with session.begin():
            job = Job.by_id(job_id)
            tasks = job.recipesets[0].recipes[0].tasks
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[0].name, '/distribution/check-install')
            self.assertEqual(tasks[1].name, self.task.name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1188539
    def test_uses_new_check_install_task_by_default(self):
        with session.begin():
            distro = data_setup.create_distro(osmajor=u'Fedora29')
            data_setup.create_distro_tree(distro=distro)
        self._verify_check_install(distro=distro)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1806987
    def test_uses_original_install_task_on_older_distros(self):
        with session.begin():
            distro = data_setup.create_distro(osmajor=u'RedHatEnterpriseLinux7')
            data_setup.create_distro_tree(distro=distro)
        self._verify_check_install(distro=distro)
