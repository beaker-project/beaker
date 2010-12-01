
import unittest
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.server.test import data_setup

class TestJobsController(unittest.TestCase):

    def setUp(self):
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.user = data_setup.create_user()
        data_setup.create_distro(name=u'BlueShoeLinux5-5')
        data_setup.create_task(name=u'/distribution/install')
        session.flush()

    def test_uploading_job_without_recipeset_raises_exception(self):
        xmljob = XmlJob(xmltramp.parse('''
            <job>
                <whiteboard>job with norecipesets</whiteboard>
            </job>
            '''))
        self.assertRaises(BX, lambda: self.controller.process_xmljob(xmljob, self.user))

    def test_uploading_job_with_invalid_hostRequires_raises_exception(self):
        xmljob = XmlJob(xmltramp.parse('''
            <job>
                <whiteboard>job with invalid hostRequires</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires>
                            <memory op=">=" value="500MB" />
                        </hostRequires>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            '''))
        self.assertRaises(BX, lambda: self.controller.process_xmljob(xmljob, self.user))

    def test_job_xml_can_be_roundtripped(self):
        # Ideally the logic for parsing job XML into a Job instance would live in model code,
        # so that this test doesn't have to go through the web layer...
        complete_job_xml = pkg_resources.resource_string('bkr.server.test', 'complete-job.xml')
        xmljob = XmlJob(xmltramp.parse(complete_job_xml))
        job = self.controller.process_xmljob(xmljob, self.user)
        roundtripped_xml = job.to_xml(clone=True).toprettyxml(indent='    ')
        self.assertEquals(roundtripped_xml, complete_job_xml)
