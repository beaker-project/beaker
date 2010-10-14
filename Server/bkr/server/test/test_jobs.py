
import unittest
import xmltramp
from turbogears.database import session
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.server.test import data_setup

class TestJobsController(unittest.TestCase):

    destructive = True

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
