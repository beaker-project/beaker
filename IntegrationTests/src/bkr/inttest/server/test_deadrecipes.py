
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import lxml.etree
from bkr.server.model import TaskStatus, Job, LabControllerDistroTree
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction, fix_beakerd_repodata_perms, \
    DatabaseTestCase
from bkr.server.tools import beakerd
from bkr.server.jobs import Jobs


class TestBeakerd(DatabaseTestCase):

    @with_transaction
    def setUp(cls):
        # Create two unique labs
        lab1 = data_setup.create_labcontroller()
        lab2 = data_setup.create_labcontroller()
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
        system1 = data_setup.create_system(owner=user, lab_controller=lab1)
        system2 = data_setup.create_system(owner=user, lab_controller=lab1)

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
                        <hostRequires>
                            <hypervisor value=""/>
                        </hostRequires>
                        <task name="/distribution/check-install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
                 ''' 
        xmljob1 = lxml.etree.fromstring(job % (cls.distro_tree1.distro.name,
                                               cls.distro_tree1.distro.name))
        xmljob2 = lxml.etree.fromstring(job % (cls.distro_tree2.distro.name,
                                               cls.distro_tree2.distro.name))

        cls.job1 = Jobs().process_xmljob(xmljob1, user)
        cls.job2 = Jobs().process_xmljob(xmljob2, user)

    @classmethod
    def tearDownClass(cls):
        fix_beakerd_repodata_perms()

    def test_01_invalid_system_distro_combo(self):
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            self.assertEqual(Job.by_id(self.job1.id).status, TaskStatus.aborted)
            self.assertEqual(Job.by_id(self.job2.id).status, TaskStatus.processed)

    def test_02_abort_dead_recipes(self):
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job =  Job.by_id(self.job2.id)
            self.assertEqual(job.status, TaskStatus.processed)
            # check if rows in system_recipe_map
            self.assertNotEqual(len(job.recipesets[0].recipes[0].systems), 0)
            # Remove distro_tree2 from lab1, should cause remaining recipe to abort.
            for lca in self.distro_tree2.lab_controller_assocs[:]:
                session.delete(lca)
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job =  Job.by_id(self.job2.id)
            self.assertEqual(job.status, TaskStatus.aborted)
            # https://bugzilla.redhat.com/show_bug.cgi?id=1173376
            # check if no rows system_recipe_map
            self.assertEqual(len(job.recipesets[0].recipes[0].systems), 0)
