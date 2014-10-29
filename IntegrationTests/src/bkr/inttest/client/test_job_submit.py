
# vim: set fileencoding=utf-8 :

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientTestCase
from bkr.server.model import Distro
import pkg_resources

class JobSubmitTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        data_setup.create_product(product_name=u'the_product')
        data_setup.create_group(group_name='somegroup')
        data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')

    def test_submit_job(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            group = data_setup.create_group(group_name='somegroup')
            user.groups.append(group)

        # Test submitting on behalf of user's group
        config = create_client_config(username=user.user_name,
                                       password='password')
        out = run_client(['bkr', 'job-submit',
                pkg_resources.resource_filename('bkr.inttest', 'complete-job.xml')],
                         config=config)
        self.assert_(out.startswith('Submitted:'), out)

    def job_xml_with_encoding(self, encoding, funny_chars):
        return (u'''<?xml version="1.0" encoding="%s"?>
            <job>
                <whiteboard>job with encoding in XML declaration %s</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
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
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        out = run_client(['bkr', 'job-submit'], input=jobxml)
        self.assertIn("Submitted: ['J:", out)
