
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from threading import Thread, Event
import xmltramp
import pkg_resources
from turbogears.database import session
from bkr.server.jobxml import XmlJob
from bkr.server.bexceptions import BX, StaleTaskStatusException
from bkr.inttest import data_setup, fix_beakerd_repodata_perms
from bkr.server.model import TaskStatus, TaskResult, Watchdog, RecipeSet, Distro, \
        Job, Recipe, System, SystemResource
from bkr.server.tools import beakerd

def watchdogs_for_job(job):
    return Watchdog.query.join('recipe', 'recipeset', 'job')\
            .filter(RecipeSet.job == job).all() + \
           Watchdog.query.join('recipetask', 'recipe', 'recipeset', 'job')\
            .filter(RecipeSet.job == job).all()

class TestUpdateStatus(unittest.TestCase):

    def setUp(self):
        session.begin()
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.user = data_setup.create_user()
        if not Distro.by_name(u'BlueShoeLinux5-5'):
            data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')
        session.flush()

    def tearDown(self):
        session.commit()
        session.close()

    def test_abort_recipe_bubbles_status_to_job(self):
        xmljob = XmlJob(xmltramp.parse('''
            <job>
                <whiteboard>job </whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            '''))
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()
        for recipeset in job.recipesets:
            for recipe in recipeset.recipes:
                recipe.process()
                recipe.queue()
                recipe.schedule()
                recipe.waiting()

        # Abort the first recipe.
        job.recipesets[0].recipes[0].abort()
        job.update_status()

        # Verify that it and its children are aborted.
        self.assertEquals(job.recipesets[0].recipes[0].status, TaskStatus.aborted)
        for task in job.recipesets[0].recipes[0].tasks:
            self.assertEquals(task.status, TaskStatus.aborted)

        # Verify that the second recipe and its children are still waiting.
        self.assertEquals(job.recipesets[1].recipes[0].status, TaskStatus.waiting)
        for task in job.recipesets[1].recipes[0].tasks:
            self.assertEquals(task.status, TaskStatus.waiting)

        # Verify that the job still shows waiting.
        self.assertEquals(job.status, TaskStatus.waiting)

        # Abort the second recipe now.
        job.recipesets[1].recipes[0].abort()
        job.update_status()

        # Verify that the whole job shows aborted now.
        self.assertEquals(job.status, TaskStatus.aborted)

    # https://bugzilla.redhat.com/show_bug.cgi?id=903935
    def test_finished_recipe_with_unstarted_guests(self):
        # host completes, but guest never started
        job = data_setup.create_job(num_recipes=1, num_guestrecipes=1)
        data_setup.mark_job_waiting(job)
        data_setup.mark_recipe_running(job.recipesets[0].recipes[0], only=True)
        job.recipesets[0].recipes[0].tasks[-1].stop()
        job.update_status()
        self.assertEquals(job.recipesets[0].recipes[0].status,
                TaskStatus.completed)
        self.assertEquals(job.recipesets[0].recipes[0].guests[0].status,
                TaskStatus.aborted)

        # host aborts, but guest never started
        job = data_setup.create_job(num_recipes=1, num_guestrecipes=1)
        data_setup.mark_job_waiting(job)
        job.recipesets[0].recipes[0].abort(msg='blorf')
        job.update_status()
        self.assertEquals(job.recipesets[0].recipes[0].status,
                TaskStatus.aborted)
        self.assertEquals(job.recipesets[0].recipes[0].guests[0].status,
                TaskStatus.aborted)

    def test_update_status_can_be_roundtripped_35508(self):
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'job_35508.xml')
        xmljob = XmlJob(xmltramp.parse(complete_job_xml))

        data_setup.create_tasks(xmljob)
        session.flush()
        
        # Import the job xml
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()

        # Mark job waiting
        data_setup.mark_job_waiting(job)
        session.flush()

        # watchdog's should exist 
        self.assertNotEqual(len(watchdogs_for_job(job)), 0)

        # Play back the original jobs results and status
        data_setup.playback_job_results(job, xmljob)
        session.flush()
        
        # Verify that the original status and results match
        self.assertEquals(TaskStatus.from_string(xmljob.wrappedEl('status')), job.status)
        self.assertEquals(TaskResult.from_string(xmljob.wrappedEl('result')), job.result)
        for i, recipeset in enumerate(xmljob.iter_recipeSets()):
            for j, recipe in enumerate(recipeset.iter_recipes()):
                self.assertEquals(TaskStatus.from_string(recipe.wrappedEl('status')),
                        job.recipesets[i].recipes[j].status)
                self.assertEquals(TaskResult.from_string(recipe.wrappedEl('result')),
                        job.recipesets[i].recipes[j].result)
                for k, task in enumerate(recipe.iter_tasks()):
                    self.assertEquals(TaskStatus.from_string(task.status),
                            job.recipesets[i].recipes[j].tasks[k].status)
                    self.assertEquals(TaskResult.from_string(task.result),
                            job.recipesets[i].recipes[j].tasks[k].result)

        # No watchdog's should exist when the job is complete
        self.assertEquals(len(watchdogs_for_job(job)), 0)

    def test_update_status_can_be_roundtripped_40214(self):
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'job_40214.xml')
        xmljob = XmlJob(xmltramp.parse(complete_job_xml))

        data_setup.create_tasks(xmljob)
        session.flush()
        
        # Import the job xml
        job = self.controller.process_xmljob(xmljob, self.user)
        session.flush()

        # Mark job waiting
        data_setup.mark_job_waiting(job)
        session.flush()

        # watchdog's should exist 
        self.assertNotEqual(len(watchdogs_for_job(job)), 0)

        # Play back the original jobs results and status
        data_setup.playback_job_results(job, xmljob)
        session.flush()
        
        # Verify that the original status and results match
        self.assertEquals(TaskStatus.from_string(xmljob.wrappedEl('status')), job.status)
        self.assertEquals(TaskResult.from_string(xmljob.wrappedEl('result')), job.result)
        for i, recipeset in enumerate(xmljob.iter_recipeSets()):
            for j, recipe in enumerate(recipeset.iter_recipes()):
                self.assertEquals(TaskStatus.from_string(recipe.wrappedEl('status')),
                        job.recipesets[i].recipes[j].status)
                self.assertEquals(TaskResult.from_string(recipe.wrappedEl('result')),
                        job.recipesets[i].recipes[j].result)
                for k, task in enumerate(recipe.iter_tasks()):
                    self.assertEquals(TaskStatus.from_string(task.status),
                            job.recipesets[i].recipes[j].tasks[k].status)
                    self.assertEquals(TaskResult.from_string(task.result),
                            job.recipesets[i].recipes[j].tasks[k].result)

        # No watchdog's should exist when the job is complete
        self.assertEquals(len(watchdogs_for_job(job)), 0)

class ConcurrentUpdateTest(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        fix_beakerd_repodata_perms()

    # https://bugzilla.redhat.com/show_bug.cgi?id=807237
    def test_concurrent_recipe_completion(self):
        # This test simulates two recipes finishing at the same time. So we 
        # have two concurrent transactions both updating the respective task states.
        # Previously there was no separate job.update_status() step, so the two 
        # transactions would update the job status using out-of-date values in 
        # both transactions, leaving the job running.
        with session.begin():
            recipe1 = data_setup.create_recipe()
            recipe2 = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe1, recipe2])
            assert len(recipe1.tasks) == 1
            assert len(recipe2.tasks) == 1
            data_setup.mark_recipe_running(recipe1)
            data_setup.mark_recipe_running(recipe2)
            recipe1.tasks[-1].pass_(u'/', 0, u'Pass')
            recipe2.tasks[-1].pass_(u'/', 0, u'Pass')

        # Complete the recipes "concurrently" in two separate transactions
        class RecipeCompletionThread(Thread):
            def __init__(self, recipe_id=None, **kwargs):
                super(RecipeCompletionThread, self).__init__(**kwargs)
                self.recipe_id = recipe_id
                self.ready_evt = Event()
                self.continue_evt = Event()
            def run(self):
                session.begin()
                recipe = Recipe.by_id(self.recipe_id)
                self.ready_evt.set()
                self.continue_evt.wait()
                recipe.tasks[-1].stop()
                session.commit()
        thread1 = RecipeCompletionThread(name='recipe1', recipe_id=recipe1.id)
        thread2 = RecipeCompletionThread(name='recipe2', recipe_id=recipe2.id)
        thread1.start()
        thread2.start()
        # Wait for both threads to start their transactions
        thread1.ready_evt.wait()
        thread2.ready_evt.wait()
        # Allow recipe 1 to complete
        thread1.continue_evt.set()
        thread1.join()
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(recipe1.status, TaskStatus.completed)
            self.assertEquals(recipe1.ptasks, 1)
            self.assertEquals(job.status, TaskStatus.running)
            self.assertEquals(job.ptasks, 1)
        # Now recipe 2 completes
        thread2.continue_evt.set()
        thread2.join()
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(recipe2.status, TaskStatus.completed)
            self.assertEquals(recipe2.ptasks, 1)
            self.assertEquals(job.status, TaskStatus.completed)
            self.assertEquals(job.ptasks, 2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=715226
    def test_cancel_while_scheduling(self):
        # This test simulates a user cancelling their job at the same time as 
        # beakerd is scheduling it. beakerd assigns a system and creates 
        # a watchdog and sets the recipe status to Waiting, then it's 
        # overwritten by another transaction setting the status to Cancelled.
        with session.begin():
            lab_controller = data_setup.create_labcontroller()
            system = data_setup.create_system(shared=True,
                    lab_controller=lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20',
                    lab_controllers=[lab_controller])
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.by_id(job.id)
            system = System.query.get(system.id)
            self.assertEquals(job.status, TaskStatus.queued)
            self.assertEquals(job.recipesets[0].recipes[0].systems, [system])

        # Two "concurrent" transactions, in the first one beakerd has 
        # scheduled the recipe and is about to commit...
        class ScheduleThread(Thread):
            def __init__(self, **kwargs):
                super(ScheduleThread, self).__init__(**kwargs)
                self.ready_evt = Event()
                self.continue_evt = Event()
            def run(self):
                session.begin()
                recipe = Job.by_id(job.id).recipesets[0].recipes[0]
                assert recipe.status == TaskStatus.queued
                self.ready_evt.set()
                self.continue_evt.wait()
                try:
                    beakerd.schedule_queued_recipe(recipe.id)
                    assert False, 'should raise'
                except StaleTaskStatusException:
                    pass # expected
                session.rollback()

        # ... and in the second transaction the user is cancelling the recipe.
        class CancelThread(Thread):
            def __init__(self, **kwargs):
                super(CancelThread, self).__init__(**kwargs)
                self.ready_evt = Event()
                self.continue_evt = Event()
            def run(self):
                session.begin()
                recipe = Job.by_id(job.id).recipesets[0].recipes[0]
                assert not recipe.watchdog
                assert not recipe.resource
                recipe.recipeset.cancel()
                self.ready_evt.set()
                self.continue_evt.wait()
                session.commit()

        sched_thread = ScheduleThread()
        cancel_thread = CancelThread()
        sched_thread.start()
        cancel_thread.start()
        sched_thread.ready_evt.wait()
        cancel_thread.ready_evt.wait()
        sched_thread.continue_evt.set()
        cancel_thread.continue_evt.set()
        sched_thread.join()
        cancel_thread.join()
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(job.status, TaskStatus.cancelled)
            self.assertEquals(job.recipesets[0].recipes[0].watchdog, None)
            self.assertEquals(system.open_reservation, None)

class RecoveryTest(unittest.TestCase):

    # These tests assert that the update_status method can recover the various 
    # bad states that have been observed in the past due to race conditions in 
    # status updates.
    # It should no longer be possible to get into the bad states which we are 
    # testing in this class. The tests above assert that.

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    # https://bugzilla.redhat.com/show_bug.cgi?id=807237
    def test_recovers_running_job_with_completed_recipes(self):
        # job with two recipes, both Completed, but job is Running
        # and systems are still assigned
        job = data_setup.create_job(num_recipes=2)
        data_setup.mark_job_running(job)
        systems = [r.resource.system for r in job.all_recipes]
        job.recipesets[0].recipes[0].tasks[-1].stop()
        job.recipesets[0].recipes[0]._update_status()
        job.recipesets[0].recipes[1].tasks[-1].stop()
        job.recipesets[0].recipes[1]._update_status()
        session.flush()
        self.assertEquals(job.recipesets[0].recipes[0].status,
                TaskStatus.completed)
        self.assertEquals(job.recipesets[0].recipes[1].status,
                TaskStatus.completed)
        self.assertEquals(job.recipesets[0].status, TaskStatus.running)
        self.assertEquals(job.status, TaskStatus.running)
        self.assert_(systems[0].open_reservation is not None)
        self.assert_(systems[1].open_reservation is not None)

        job.update_status()
        session.flush()
        session.expire_all()
        self.assertEquals(systems[0].open_reservation, None)
        self.assertEquals(systems[1].open_reservation, None)
        self.assertEquals(job.recipesets[0].status, TaskStatus.completed)
        self.assertEquals(job.status, TaskStatus.completed)

    # https://bugzilla.redhat.com/show_bug.cgi?id=715226
    def test_recovers_leaked_system(self):
        # recipe is cancelled but system has still been assigned
        recipe = data_setup.create_recipe()
        data_setup.create_job_for_recipes([recipe])
        recipe.cancel()
        recipe.recipeset.job.update_status()
        system = data_setup.create_system()
        recipe.resource = SystemResource(system=system)
        recipe.resource.allocate()
        recipe.watchdog = Watchdog()
        session.flush()
        self.assert_(system.open_reservation is not None)
        self.assert_(system.open_reservation is recipe.resource.reservation)
        self.assert_(system.user is not None)
        self.assert_(recipe.watchdog is not None)

        recipe.recipeset.job.update_status()
        session.flush()
        session.expire_all()
        self.assertEquals(system.open_reservation, None)
        self.assertEquals(system.user, None)
        self.assertEquals(recipe.watchdog, None)

    def test_recovers_completed_recipe_with_running_tasks(self):
        job = data_setup.create_job()
        data_setup.mark_job_running(job)
        job.abort()
        job.update_status()
        job.recipesets[0].recipes[0].tasks[-1].status = TaskStatus.running
        session.flush()

        job.update_status()
        self.assertEquals(job.status, TaskStatus.aborted)
        self.assertEquals(job.recipesets[0].recipes[0].status, TaskStatus.aborted)
        self.assertEquals(job.recipesets[0].recipes[0].tasks[-1].status, TaskStatus.aborted)
