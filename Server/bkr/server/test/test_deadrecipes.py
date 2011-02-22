import unittest

from time import sleep
import time
from bkr.server.model import TaskStatus, Job, LabControllerDistro
import sqlalchemy.orm
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.tools import beakerd
import threading

class TestBeakerd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        data_setup.create_test_env('min')
        session.flush()

    def setUp(self):
        # Create two unique labs
        lab1 = data_setup.create_labcontroller(fqdn='lab_%d' %
                                               int(time.time() * 1000))
        lab2 = data_setup.create_labcontroller(fqdn='lab_%d' %
                                               int(time.time() * 1000))

        # Create two distros and only put one in each lab.
        self.distro1 = data_setup.create_distro()
        self.distro2 = data_setup.create_distro()
        session.flush()
        self.distro1.lab_controller_assocs = [LabControllerDistro(
                                                           lab_controller=lab2
                                                                 )
                                             ]
        self.distro2.lab_controller_assocs = [LabControllerDistro(
                                                           lab_controller=lab1
                                                                 )
                                             ]

        # Create two systems but only put them in lab1.
        system1 = data_setup.create_system()
        system2 = data_setup.create_system()
        system1.lab_controller = lab1
        system2.lab_controller = lab1

        # Create two jobs, one requiring distro1 and one requiring distro2
        self.job1 = data_setup.create_job(whiteboard=u'job_1', 
                                               distro=self.distro1)
        self.job2 = data_setup.create_job(whiteboard=u'job_2', 
                                               distro=self.distro2)
        session.flush()

    def test_invalid_system_distro_combo(self):
        beakerd.new_recipes()
        self.assertEqual(self.job1.status, TaskStatus.by_name(u'Aborted'))
        self.assertEqual(self.job2.status, TaskStatus.by_name(u'Processed'))


    def test_dead_recipes(self):
        beakerd.new_recipes()
        beakerd.processed_recipesets()
        self.assertEqual(self.job2.status, TaskStatus.by_name(u'Queued'))
        # Remove distro2 from lab1, should cause remaining recipe to abort.
        for lab in self.distro2.lab_controllers[:]:
            self.distro2.lab_controllers.remove(lab)
        beakerd.dead_recipes()
        self.assertEqual(self.job2.status, TaskStatus.by_name(u'Aborted'))
        

    @classmethod
    def teardownClass(cls):
        pass
