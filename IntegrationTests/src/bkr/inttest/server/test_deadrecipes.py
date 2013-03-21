import unittest
import xmltramp

from time import sleep
import time
from bkr.server.model import TaskStatus, Job, LabControllerDistroTree, Distro
import sqlalchemy.orm
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.server.tools import beakerd
from bkr.server.jobxml import XmlJob
from bkr.server.jobs import Jobs

import threading

class TestBeakerd(unittest.TestCase):

    @classmethod
    @with_transaction
    def setUpClass(cls):
        # Create two unique labs
        lab1 = data_setup.create_labcontroller(fqdn=u'lab_%d' %
                                               int(time.time() * 1000))
        lab2 = data_setup.create_labcontroller(fqdn=u'lab_%d' %
                                               int(time.time() * 1000))

        # Create two distros and only put one in each lab.
        cls.distro_tree1 = data_setup.create_distro_tree()
        cls.distro_tree2 = data_setup.create_distro_tree()
        session.flush()
        cls.distro_tree1.lab_controller_assocs = [LabControllerDistroTree(
                lab_controller=lab2, url=u'http://notimportant')]
        cls.distro_tree2.lab_controller_assocs = [LabControllerDistroTree(
                lab_controller=lab1, url=u'http://notimportant')]

        # Create a user
        user = data_setup.create_user()

        # Create two systems but only put them in lab1.
        system1 = data_setup.create_system(owner=user)
        system2 = data_setup.create_system(owner=user)
        system1.lab_controller = lab1
        system2.lab_controller = lab1

        session.flush()

        # Create two jobs, one requiring distro_tree1 and one requiring distro_tree2
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
        xmljob1 = XmlJob(xmltramp.parse(job % (cls.distro_tree1.distro.name,
                cls.distro_tree1.distro.name)))
        xmljob2 = XmlJob(xmltramp.parse(job % (cls.distro_tree2.distro.name,
                cls.distro_tree2.distro.name)))

        cls.job1 = Jobs().process_xmljob(xmljob1, user)
        cls.job2 = Jobs().process_xmljob(xmljob2, user)

    def test_01_invalid_system_distro_combo(self):
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            self.assertEqual(Job.by_id(self.job1.id).status, TaskStatus.aborted)
            self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.processed)


    def test_02_abort_dead_recipes(self):
        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.queued)
            # Remove distro_tree2 from lab1, should cause remaining recipe to abort.
            for lca in self.distro_tree2.lab_controller_assocs[:]:
                session.delete(lca)
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.aborted)
