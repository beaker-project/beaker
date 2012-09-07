
# vim: set fileencoding=utf-8 :

import unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client
from bkr.server.model import Distro
import pkg_resources

class JobSubmitTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        data_setup.create_product(product_name=u'the_product')
        if not Distro.by_name(u'BlueShoeLinux5-5'):
            data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')

    def test_submit_job(self):
        out = run_client(['bkr', 'job-submit',
                pkg_resources.resource_filename('bkr.inttest', 'complete-job.xml')])
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
