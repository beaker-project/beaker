
# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest.assertions import character_diff_message
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase
from bkr.server.model import Job

class JobCloneTest(ClientTestCase):

    maxDiff = None

    def setUp(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(distro_name='DansAwesomeLinux6.5')
            self.job = data_setup.create_completed_job(whiteboard="foo", distro_tree=distro_tree)
            self.user_foo = data_setup.create_user(password='foo')
            self.user_bar = data_setup.create_user(password='bar')
            self.bot = data_setup.create_user(password='bot')
            # Add bot as delegate submission of foo
            self.user_foo.add_submission_delegate(self.bot, service=u'testdata')

    def test_can_clone_job(self):
        out = run_client(['bkr', 'job-clone', self.job.t_id])
        self.assert_(out.startswith('Submitted:'))

    def test_can_clone_recipeset(self):
        out = run_client(['bkr', 'job-clone', self.job.recipesets[0].t_id])
        self.assert_(out.startswith('Submitted:'))

    def test_can_print_xml(self):
        expected_xml = (
            '<?xml version=\'1.0\' encoding=\'utf8\'?>\n'
            '<job retention_tag="scratch">'
            '<whiteboard>foo</whiteboard>'
            '<recipeSet priority="Normal">'
            '<recipe whiteboard="" role="STANDALONE" ks_meta="" kernel_options="" kernel_options_post="">'
            '<autopick random="false"/>'
            '<watchdog/>'
            '<packages/>'
            '<ks_appends/>'
            '<repos/>'
            '<distroRequires>'
            '<and>'
            '<distro_family op="=" value="DansAwesomeLinux6"/>'
            '<distro_variant op="=" value="Server"/>'
            '<distro_name op="=" value="DansAwesomeLinux6.5"/>'
            '<distro_arch op="=" value="i386"/>'
            '</and>'
            '</distroRequires>'
            '<hostRequires>'
            '<system_type value="Machine"/>'
            '</hostRequires>'
            '<partitions/>'
            '<task name="/distribution/reservesys" role="STANDALONE"/>'
            '</recipe></recipeSet></job>')
        out = run_client(['bkr', 'job-clone','--xml', self.job.t_id])
        self.assert_('Submitted:' in out)
        actual_xml = out[:out.find('Submitted')]
        self.assertEqual(expected_xml.strip(), actual_xml.strip(),
                         character_diff_message(expected_xml.strip(), actual_xml.strip()))

    def test_can_print_prettyxml(self):
        expected_xml = """
<?xml version='1.0' encoding='utf8'?>
<job retention_tag="scratch">
  <whiteboard>foo</whiteboard>
  <recipeSet priority="Normal">
    <recipe whiteboard="" role="STANDALONE" ks_meta="" kernel_options="" kernel_options_post="">
      <autopick random="false"/>
      <watchdog/>
      <packages/>
      <ks_appends/>
      <repos/>
      <distroRequires>
        <and>
          <distro_family op="=" value="DansAwesomeLinux6"/>
          <distro_variant op="=" value="Server"/>
          <distro_name op="=" value="DansAwesomeLinux6.5"/>
          <distro_arch op="=" value="i386"/>
        </and>
      </distroRequires>
      <hostRequires>
        <system_type value="Machine"/>
      </hostRequires>
      <partitions/>
      <task name="/distribution/reservesys" role="STANDALONE"/>
    </recipe>
  </recipeSet>
</job>"""
        out = run_client(['bkr', 'job-clone','--prettyxml', self.job.t_id])
        self.assert_('Submitted:' in out)
        actual_xml = out[:out.find('Submitted')]
        self.assertMultiLineEqual(expected_xml.strip(), actual_xml.strip())

    def test_can_dryrun(self):
        out = run_client(['bkr', 'job-clone','--dryrun', self.job.t_id])
        self.assert_('Submitted:' not in out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=595512
    def test_invalid_taskspec(self):
        try:
            run_client(['bkr', 'job-clone', '12345'])
            fail('should raise')
        except ClientError, e:
            self.assert_('Invalid taskspec' in e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1014623
    def test_nonascii_chars_in_job_xml(self):
        with session.begin():
            job = data_setup.create_completed_job(
                    whiteboard=u'Фёдор Михайлович Достоевский')
        out = run_client(['bkr', 'job-clone', job.t_id])
        self.assertIn('Submitted:', out)
        out = run_client(['bkr', 'job-clone', '--xml', job.t_id])
        self.assertIn('Submitted:', out)
        out = run_client(['bkr', 'job-clone', '--prettyxml', job.t_id])
        self.assertIn('Submitted:', out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215138
    def test_delegate_submission_fails(self):
        user_bar_name = self.user_bar.user_name
        bot_name = self.bot.user_name
        with self.assertRaises(ClientError) as cm:
            run_client(['bkr', 'job-clone',
                '--username', bot_name,
                '--password', 'bot',
                '--job-owner', user_bar_name,
                self.job.t_id])
        error = cm.exception
        msg = '%s is not a valid submission delegate for %s' \
            % (bot_name, user_bar_name)
        self.assert_(msg in str(error))

    def test_can_delegate_submission(self):
        user_foo_name = self.user_foo.user_name
        bot_name = self.bot.user_name
        out = run_client(['bkr', 'job-clone',
            '--username', bot_name,
            '--password', 'bot',
            '--job-owner', user_foo_name,
            self.job.t_id])
        self.assert_('Submitted:' in out)
        last_job = Job.query.order_by(Job.id.desc()).first()
        self.assertEqual(user_foo_name, last_job.owner.user_name)