
import unittest
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX
from bkr.server.test import data_setup
from bkr.server.tools import beakerd

class TestLabController(unittest.TestCase):

    def setUp(self):
        from bkr.server.jobs import Jobs
        self.lc = data_setup.create_labcontroller(fqdn=u'lab.domain.com')
        user = data_setup.create_user()
        system = data_setup.create_system(owner=user)
        distro = data_setup.create_distro()
        xmljob = XmlJob(xmltramp.parse('''
            <job>
                <whiteboard>job with invalid hostRequires</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="%s" />
                        </distroRequires>
                        <hostRequires>
                            <hostname op="=" value="%s"/>
                        </hostRequires>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
                 ''' % (distro, system.fqdn)))
        controller = Jobs()
        system.lab_controller = self.lc
        data_setup.create_task(name=u'/distribution/install')
        session.flush()
        self.job = controller.process_xmljob(xmljob, user)
        session.flush()
        beakerd.new_recipes()
        beakerd.processed_recipesets()
        

    def test_disable_lab_controller(self):
        self.lc.disabled = True
        session.save_or_update(self.lc)
        session.flush()
        self.assertEquals(beakerd.queued_recipes(), False)

    def test_enable_lab_controller(self):
        self.lc.disabled = False
        session.save_or_update(self.lc)
        session.flush()
        self.assertEquals(beakerd.queued_recipes(), True)

