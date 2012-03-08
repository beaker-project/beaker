import unittest
import xmltramp

from time import sleep
import time
from bkr.server.model import TaskStatus, Job, LabControllerDistro, Distro
import sqlalchemy.orm
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.server.tools import beakerd
from bkr.server.jobxml import XmlJob
from bkr.server.jobs import Jobs

import threading

class TestBeakerd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create two unique labs
        lab1 = data_setup.create_labcontroller(fqdn=u'lab_%d' %
                                               int(time.time() * 1000))
        lab2 = data_setup.create_labcontroller(fqdn=u'lab_%d' %
                                               int(time.time() * 1000))

        # Create two distros and only put one in each lab.
        cls.distro1 = data_setup.create_distro()
        cls.distro2 = data_setup.create_distro()
        session.flush()
        cls.distro1.lab_controller_assocs = [LabControllerDistro(
                                                           lab_controller=lab2
                                                                 )
                                             ]
        cls.distro2.lab_controller_assocs = [LabControllerDistro(
                                                           lab_controller=lab1
                                                                 )
                                             ]

        # Create a user
        user = data_setup.create_user()

        # Create two systems but only put them in lab1.
        system1 = data_setup.create_system(owner=user)
        system2 = data_setup.create_system(owner=user)
        system1.lab_controller = lab1
        system2.lab_controller = lab1

        data_setup.create_task(name=u'/distribution/install')

        # Create two jobs, one requiring distro1 and one requiring distro2
        job = '''
            <job>
                <whiteboard>%s</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="%s" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
                 ''' 
        xmljob1 = XmlJob(xmltramp.parse(job % (cls.distro1.name, cls.distro1.name)))
        xmljob2 = XmlJob(xmltramp.parse(job % (cls.distro2.name, cls.distro2.name)))

        cls.job1 = Jobs().process_xmljob(xmljob1, user)
        cls.job2 = Jobs().process_xmljob(xmljob2, user)
        session.flush()

    def test_01_invalid_system_distro_combo(self):
        beakerd.new_recipes()
        self.assertEqual(Job.by_id(self.job1.id).status, TaskStatus.aborted)
        self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.processed)


    def test_02_dead_recipes(self):
        beakerd.new_recipes()
        beakerd.processed_recipesets()
        self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.queued)
        # Remove distro2 from lab1, should cause remaining recipe to abort.
        distro = Distro.by_id(self.distro2.id)
        for lab in distro.lab_controllers[:]:
            distro.lab_controllers.remove(lab)
        session.flush()
        beakerd.dead_recipes()
        self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.aborted)
        

    @classmethod
    def teardownClass(cls):
        pass
