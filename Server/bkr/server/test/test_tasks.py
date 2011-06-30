
import unittest
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.model import TaskStatus, RecipeSet
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.server.test import data_setup
from bkr.server.tools import beakerd

class TestTasks(unittest.TestCase):

    def setUp(self):
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.task = data_setup.create_task(name=u'/fake/task/here')
        distro = data_setup.create_distro()
        self.user = data_setup.create_user()
        self.xmljob = XmlJob(xmltramp.parse('''
            <job>
                <whiteboard>job with fake task</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="%s" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="%s" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            ''' % (distro.name, self.task.name)))
        session.flush()

    def test_enable_task(self):
        self.task.valid=True
        session.flush()
        self.controller.process_xmljob(self.xmljob, self.user)
        
    def test_disable_task(self):
        try:
            session.begin()
            self.task.valid=False
            session.flush()
            self.assertRaises(BX, lambda: self.controller.process_xmljob(self.xmljob, self.user))
        finally:
            session.rollback()
            session.close()
