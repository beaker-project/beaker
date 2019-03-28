
# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientTestCase, ClientError
from bkr.server.model import Job
import pkg_resources

class JobSubmitTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        data_setup.create_product(product_name=u'the_product')
        data_setup.create_group(group_name=u'somegroup')
        self.user_foo = data_setup.create_user(password=u'foo')
        self.user_bar = data_setup.create_user(password=u'bar')
        self.bot = data_setup.create_user(password=u'bot')
        # Add bot as delegate submission of foo
        self.user_foo.add_submission_delegate(self.bot, service=u'testdata')

    def test_submit_job(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            group = data_setup.create_group(group_name=u'somegroup')
            group.add_member(user)

        # Test submitting on behalf of user's group
        config = create_client_config(username=user.user_name,
                                       password=u'password')
        out = run_client(['bkr', 'job-submit',
                pkg_resources.resource_filename('bkr.inttest', 'complete-job.xml')],
                         config=config)
        self.assert_(out.startswith('Submitted:'), out)

    def test_missing_distro_and_distroRequires_element(self):
        faulty_xml = '''<job>
                <whiteboard>job with encoding in XML declaration</whiteboard>
                <recipeSet>
                    <recipe>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        with self.assertRaises(ClientError) as cm:
            run_client(['bkr', 'job-submit', '-'], input=faulty_xml)
        self.assertIn("You must define either <distroRequires/> or <distro/> element", str(cm.exception))

    def job_xml_with_encoding(self, encoding, funny_chars):
        return (u'''<?xml version="1.0" encoding="%s"?>
            <job>
                <whiteboard>job with encoding in XML declaration %s</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_family op="=" value="BlueShoeLinux5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            ''' % (encoding, funny_chars)).encode(encoding)

    # https://bugzilla.redhat.com/show_bug.cgi?id=768167
    def test_doesnt_barf_on_xml_encoding_declaration(self):
        out = run_client(['bkr', 'job-submit', '-'],
                input=self.job_xml_with_encoding('UTF-8', u'яяя'))
        self.assert_(out.startswith('Submitted:'), out)
        out = run_client(['bkr', 'job-submit', '-'],
                input=self.job_xml_with_encoding('ISO-8859-1', u'äóß'))
        self.assert_(out.startswith('Submitted:'), out)
        # This should work, but it seems to be a bug in xml.dom.minidom:
        # http://bugs.python.org/issue15877
        #out = run_client(['bkr', 'job-submit', '-'],
        #        input=self.job_xml_with_encoding('ISO-2022-JP', u'日本語'))
        #self.assert_(out.startswith('Submitted:'), out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1142714
    def test_no_args_reads_from_stdin(self):
        jobxml = '''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_family op="=" value="BlueShoeLinux5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/check-install" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        out = run_client(['bkr', 'job-submit'], input=jobxml)
        self.assertIn("Submitted: ['J:", out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215138
    def test_delegate_submission_fails(self):
        user_bar_name = self.user_bar.user_name
        bot_name = self.bot.user_name
        with self.assertRaises(ClientError) as cm:
            run_client(['bkr', 'job-submit',
                '--username', bot_name,
                '--password', 'bot',
                '--job-owner', user_bar_name],
                input=self.job_xml_with_encoding('UTF-8', u'яяя'))
        error = cm.exception
        msg = '%s is not a valid submission delegate for %s' \
            % (bot_name, user_bar_name)
        self.assert_(msg in str(error))

    def test_can_delegate_submission(self):
        user_foo_name = self.user_foo.user_name
        bot_name = self.bot.user_name
        out = run_client(['bkr', 'job-submit',
            '--username', bot_name,
            '--password', 'bot',
            '--job-owner', user_foo_name],
            input=self.job_xml_with_encoding('UTF-8', u'яяя'))
        self.assert_('Submitted:' in out)
        last_job = Job.query.order_by(Job.id.desc()).first()
        self.assertEqual(user_foo_name, last_job.owner.user_name)
