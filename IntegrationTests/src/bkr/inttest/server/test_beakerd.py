import unittest, datetime, os, threading
import shutil
import pkg_resources
import bkr
from bkr.server.model import TaskStatus, Job, System, User, \
        Group, SystemStatus, SystemActivity, Recipe, Cpu, LabController, \
        Provision, TaskPriority, RecipeSet, Task, SystemPermission, \
        MachineRecipe, GuestRecipe, LabControllerDistroTree, DistroTree
import sqlalchemy.orm
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import not_
from turbogears.database import session, get_engine
import xmltramp
from bkr.server.jobxml import XmlJob
from bkr.inttest import data_setup, fix_beakerd_repodata_perms
from bkr.inttest.assertions import assert_datetime_within, \
        assert_durations_not_overlapping
from bkr.server.tools import beakerd
from bkr.server.jobs import Jobs

# We capture the sent mail to avoid error spam in the logs rather than to
# check anything in particular
from bkr.inttest.mail_capture import MailCaptureThread

class TestBeakerd(unittest.TestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
        self.task_id, self.rpm_name = self.add_example_task()
        self.mail_capture = MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()
        self.disable_example_task(self.task_id)

    @classmethod
    def tearDownClass(cls):
        fix_beakerd_repodata_perms()

    # We need something in the task library to ensure per-recipe repos are
    # being created and destroyed correctly
    def add_example_task(self):
        with session.begin():
            task = data_setup.create_task()
            rpm_path = Task.get_rpm_path(task.rpm)
            shutil.copyfile(
                    pkg_resources.resource_filename('bkr.inttest.server', 'empty.rpm'),
                    rpm_path)
            return task.id, task.rpm

    def disable_example_task(self, task_id):
        with session.begin():
            task = Task.by_id(task_id)
            task.disable()

    def test_host_uses_latest_guest(self):
        # This tests that the lab controller corresponding to that
        # of the latest guest distro is used.
        with session.begin():
            host_lab_controller1= self.lab_controller
            host_lab_controller2 = data_setup.create_labcontroller()
            host_lab_controller3 = data_setup.create_labcontroller()
            host_lab_controller4 = data_setup.create_labcontroller()

            data_setup.create_system(lab_controller=host_lab_controller1)
            data_setup.create_system(lab_controller=host_lab_controller2)
            data_setup.create_system(lab_controller=host_lab_controller3)
            data_setup.create_system(lab_controller=host_lab_controller4)
            j1 = data_setup.create_job(num_guestrecipes=2)

            older_dt = data_setup.create_distro_tree()
            newer_dt = data_setup.create_distro_tree(
                lab_controllers=[host_lab_controller2])
            newer_dt.date_created = datetime.datetime.utcnow()
            older_dt.date_created = datetime.datetime.utcnow() - \
                datetime.timedelta(hours=10)

        guest_recipe1 = j1.recipesets[0].recipes[1]
        guest_recipe2 = j1.recipesets[0].recipes[2]
        self.assertTrue(type(guest_recipe1), GuestRecipe)
        self.assertTrue(type(guest_recipe2), GuestRecipe)

        guest_recipe1_id = guest_recipe1.id
        guest_recipe2_id = guest_recipe2.id
        with session.begin():
            guest_recipe1 = Recipe.by_id(guest_recipe1_id)
            guest_recipe1.distro_tree = older_dt
            guest_recipe2 = Recipe.by_id(guest_recipe2_id)
            guest_recipe2.distro_tree = newer_dt
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        j1_id = j1.id
        with session.begin():
            j1 = Job.by_id(j1_id)
            self.assertEquals(j1.status, TaskStatus.scheduled, j1.status)
            host_recipe = j1.recipesets[0].recipes[0]
            self.assertEqual(host_recipe.resource.system.lab_controller.id,
                host_lab_controller2.id, host_recipe.resource.system.lab_controller)

    def test_host_and_guest_latest_guest_distro_not_in_host_lc(self):
        # This tests the case when there are more than one guest distro trees
        # and the latest guest distro tree's lc is not available to the host,
        # so the host recipe remains queued
        with session.begin():
            host_lab_controller= self.lab_controller
            system = data_setup.create_system(lab_controller=host_lab_controller)
            j1 = data_setup.create_job(num_guestrecipes=2)

        with session.begin():
            older_dt = data_setup.create_distro_tree(
                lab_controllers=[host_lab_controller])
            # Just to make sure that this distro is a bit newer
            another_lab_controller = data_setup.create_labcontroller()
            newer_dt = data_setup.create_distro_tree(
                lab_controllers=[another_lab_controller])
            newer_dt.date_created = datetime.datetime.utcnow()
            older_dt.date_created = datetime.datetime.utcnow() - \
                datetime.timedelta(hours=10)

        guest_recipe1 = j1.recipesets[0].recipes[1]
        guest_recipe2 = j1.recipesets[0].recipes[2]
        self.assertTrue(type(guest_recipe1), GuestRecipe)
        self.assertTrue(type(guest_recipe2), GuestRecipe)

        guest_recipe1_id = guest_recipe1.id
        guest_recipe2_id = guest_recipe2.id
        with session.begin():
            guest_recipe1 = Recipe.by_id(guest_recipe1_id)
            guest_recipe1.distro_tree = older_dt
            guest_recipe2 = Recipe.by_id(guest_recipe2_id)
            guest_recipe2.distro_tree = newer_dt
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        j1_id = j1.id
        with session.begin():
            j1 = Job.by_id(j1_id)
            j1.update_status()
            self.assertEquals(j1.status, TaskStatus.queued, j1.status)

    def test_host_and_guest_no_common_lab_controllers_stay_queued(self):
        # This tests that a host recipe where the guest distro is not availble
        # in any common lab controller remains queued, rather than aborts
        with session.begin():
            host_lab_controller = self.lab_controller
            guest_lab_controller = data_setup.create_labcontroller()
            host_system = data_setup.create_system(lab_controller=host_lab_controller)
            dt_for_host = data_setup.create_distro_tree(lab_controllers=[host_lab_controller])
            dt_for_guest = data_setup.create_distro_tree(lab_controllers=[guest_lab_controller])
            j1 = data_setup.create_job(num_guestrecipes=1, distro_tree=dt_for_host)
            host_recipe = j1.recipesets[0].recipes[0]
            self.assertTrue(type(host_recipe), MachineRecipe)
            guest_recipe = j1.recipesets[0].recipes[1]
            self.assertTrue(type(guest_recipe), GuestRecipe)
            guest_recipe.distro_tree = dt_for_guest
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        j1_id = j1.id
        dt_for_guest_id = dt_for_guest.id
        with session.begin():
            j1 = Job.by_id(j1_id)
            j1.update_status()
            self.assertEquals(j1.status, TaskStatus.queued, j1.status)
            dt_for_guest = DistroTree.by_id(dt_for_guest_id)
            dt_for_guest.lab_controller_assocs.append(
                LabControllerDistroTree(lab_controller=host_lab_controller,
                    url='http://whatevs.com'))
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            j1 = Job.by_id(j1_id)
            j1.update_status()
            self.assertEquals(j1.status, TaskStatus.scheduled, j1.status)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1033032
    def test_multihost_no_common_lab_controller_stays_queued(self):
        # This tests that a multihost recipe where two recipes both have free
        # candidate systems, but they're in different labs, stays queued

        with session.begin():
            lab_controller_A = self.lab_controller
            lab_controller_B = data_setup.create_labcontroller()
            system_A1 = data_setup.create_system(lab_controller=lab_controller_A)
            system_A2 = data_setup.create_system(lab_controller=lab_controller_A)
            system_B1 = data_setup.create_system(lab_controller=lab_controller_B)
            system_B2 = data_setup.create_system(lab_controller=lab_controller_B)
            # Set up a recipe set that can run in either lab
            r1 = data_setup.create_recipe()
            r2 = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([r1,r2])
            r1.systems[:] = [system_A1, system_B1]
            r2.systems[:] = [system_A2, system_B2]
            # Ensure both recipes have a free system, but in different labs
            user = data_setup.create_user()
            system_A1.user = user
            system_B2.user = user
            data_setup.mark_job_queued(job)

        # Turn the crank
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()

        import logging
        # Check only the first recipe is scheduled at this point
        job_id = job.id
        r1_id = r1.id
        r2_id = r2.id
        system_B2_id = system_B2.id
        with session.begin():
            job = Job.by_id(job_id)
            job.update_status()
            self.assertEqual(job.status, TaskStatus.queued)
            r1 = Recipe.by_id(r1_id)
            self.assertEqual(r1.status, TaskStatus.scheduled)
            self.assertEqual(r1.resource.system.fqdn, system_B1.fqdn)
            r2 = Recipe.by_id(r2_id)
            self.assertEqual(r2.status, TaskStatus.queued)
            # Free the possible r2 system in lab B
            user = data_setup.create_user()
            system_B2 = System.by_id(system_B2_id, user)
            system_B2.user = None
        session.expire_all()

        # Check the job is scheduled once the relevant system becomes free
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.by_id(job_id)
            job.update_status()
            self.assertEqual(job.status, TaskStatus.scheduled)
            r1 = Recipe.by_id(r1_id)
            self.assertEqual(r1.status, TaskStatus.scheduled)
            r2 = Recipe.by_id(r2_id)
            self.assertEqual(r2.status, TaskStatus.scheduled)
            user = data_setup.create_user()
            system_B2 = System.by_id(system_B2_id, user)
            self.assertEqual(r2.resource.system.fqdn, system_B2.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=977562
    def test_jobs_with_no_systems_process_beyond_queued(self):
        with session.begin():
            system = data_setup. \
                create_system(lab_controller=self.lab_controller)
            r1 = data_setup.create_recipe()
            j1 = data_setup.create_job_for_recipes([r1])

            r2 = data_setup.create_recipe()
            j2 = data_setup.create_job_for_recipes([r2])

            data_setup.mark_job_queued(j1)
            r1.systems[:] = [system]
            data_setup.mark_job_running(j2, system=system)
            j1.update_status()
            j2.update_status()

        # Mark system broken and cancel the job
        with session.begin():
            system.status = SystemStatus.broken
            j2.cancel()
            j2.update_status()

        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            j2 = Job.by_id(j2.id)
            self.assertTrue(j1.status is TaskStatus.queued)
            self.assertTrue(j2.status is TaskStatus.cancelled)
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        session.expunge_all()
        # We should still be queued here.
        with session.begin():
            j1 = Job.by_id(j1.id)
            self.assertTrue(j1.status is TaskStatus.queued, j1.status)
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            self.assertTrue(j1.status is TaskStatus.aborted, j1.status)

    def test_serialized_scheduling(self):
        # This tests that our main recipes loop will schedule
        # systems correctly, without any need to manually clean
        # jobs in the test:
        #
        # Create R1
        # <run_loop>
        # R1 schedules systemB
        # Create R2, R3 (low priority)
        # <run_loop>
        # R3 schedules systemB, R2 waiting for systemA
        # Create R4, R5 (high priority)
        # Complete R1, release systemA
        # <run_loop>
        # R2 gets systemA over R4 as R2's recipeset already has a lab controller
        # assert R2, R3 are scheduled. assert R4, R5 are queued.
        orig_sqrs = beakerd.schedule_queued_recipes
        orig_psrs = beakerd.provision_scheduled_recipesets
        try:

            with session.begin():
                systemB = data_setup.create_system(lab_controller=self.lab_controller)
                systemA = data_setup.create_system(lab_controller=self.lab_controller)
                r1 = data_setup.create_recipe()
                j1 = data_setup.create_job_for_recipes([r1])
            session.expire_all()
            r1_id = r1.id
            j1_id = j1.id
            sysA_id = systemA.id
            sysB_id = systemB.id

            def mock_sqrs(run_number, guest_recipe_id=None):
                with session.begin():
                    systemA = System.by_id(sysA_id, User.by_user_name('admin'))
                    systemB = System.by_id(sysB_id, User.by_user_name('admin'))
                    if run_number == 1:
                        r1 = Recipe.by_id(r1_id)
                        r1.systems[:] = [systemB]
                    if run_number == 2:
                        r2 = Recipe.by_id(r2_id)
                        r2.systems[:] = [systemA]
                        r3 = Recipe.by_id(r3_id)
                        r3.systems[:] = [systemB]
                    if run_number == 3:
                        r4 = Recipe.by_id(r4_id)
                        r4.systems[:] = [systemA]
                        r5 = Recipe.by_id(r5_id)
                        r5.systems[:] = [systemB]
                return orig_sqrs()

            def mock_psrs(*args):
                return False

            def mock_sqrs_run_1():
                return mock_sqrs(1)

            beakerd.schedule_queued_recipes = mock_sqrs_run_1
            beakerd.provision_scheduled_recipesets = mock_psrs
            beakerd._main_recipes()
            session.expire_all()
            with session.begin():
                r1 = Recipe.by_id(r1_id)
                self.assertEqual(r1.status, TaskStatus.scheduled)
                r2 = data_setup.create_recipe()
                r3 = data_setup.create_recipe()
                j2 = data_setup.create_job_for_recipes([r2, r3])
                j2.recipesets[0].priority = TaskPriority.low
            session.expire_all()
            r2_id = r2.id
            r3_id = r3.id

            def mock_sqrs_run_2():
                return mock_sqrs(2)

            beakerd.schedule_queued_recipes = mock_sqrs_run_2
            beakerd._main_recipes()
            session.expire_all()
            with session.begin():
                r1 = Recipe.by_id(r1_id)
                r2 = Recipe.by_id(r2_id)
                r3 = Recipe.by_id(r3_id)
                self.assertEqual(r1.status, TaskStatus.scheduled)
                self.assertEqual(r2.status, TaskStatus.scheduled)
                self.assertEqual(r3.status, TaskStatus.queued)
                r4 = data_setup.create_recipe()
                r5 = data_setup.create_recipe()
                j2 = data_setup.create_job_for_recipes([r4, r5])
                j2.recipesets[0].priority = TaskPriority.high
            session.expire_all()
            r4_id = r4.id
            r5_id = r5.id

            def mock_sqrs_run_3():
                return mock_sqrs(3)

            beakerd.schedule_queued_recipes = mock_sqrs_run_3
            # Release systemA
            j1 = Job.by_id(j1_id)
            data_setup.mark_job_running(j1, only=True)
            data_setup.mark_job_complete(j1, only=True)
            beakerd._main_recipes()

            with session.begin():
                r2 = Recipe.by_id(r2_id)
                r3 = Recipe.by_id(r3_id)
                r4 = Recipe.by_id(r4_id)
                r5 = Recipe.by_id(r5_id)
                self.assertEquals(r4.status, TaskStatus.queued)
                self.assertEquals(r5.status, TaskStatus.queued)
                self.assertEquals(r3.status, TaskStatus.scheduled)
                self.assertEquals(r2.status, TaskStatus.scheduled)
        finally:
            beakerd.schedule_queued_recipes = orig_sqrs
            beakerd.provision_scheduled_recipesets = orig_psrs

    def test_schedule_bad_recipes_dont_fail_all(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lab_controller)
            r1 = data_setup.create_recipe()
            r2 = data_setup.create_recipe()
            j1 = data_setup.create_job_for_recipes([r1,r2])
            r1.systems[:] = [system]
            r2.systems[:] = [system]
            r1.process()
            r1.queue()
            r2.process()
            r2.queue()
        beakerd.update_dirty_jobs()
        aborted_recipes = [r1,r2]
        scheduled_recipes = []
        original_sqr = beakerd.schedule_queued_recipe
        # Need to pass by ref
        abort_ = [False]
        def mock_sqr(recipe_id, guest_id=None):
            if abort_[0] is True:
                raise Exception('ouch')
            else:
                abort_[0] = True
            original_sqr(recipe_id)
            scheduled_recipes = aborted_recipes.pop(
                aborted_recipes.index(Recipe.by_id(recipe_id)))

        try:
            beakerd.schedule_queued_recipe = mock_sqr
            beakerd.schedule_queued_recipes()
        finally:
            beakerd.schedule_queued_recipe = original_sqr

        for a in aborted_recipes:
            a = Recipe.by_id(a.id)
            a.recipeset.job.update_status()
            self.assertEqual(a.status, TaskStatus.aborted)
        for s in scheduled_recipes:
            s = Recipe.by_id(s.id)
            s.recipeset.job.update_status()
            self.assertEquals(s.status, TaskStatus.scheduled)

    def test_just_in_time_systems(self):
       # Expected behaviour of this test is (as of 0.11.3) the following:
       # When scheduled_queued_recipes() is called it retrieves spare_recipe
       # and r4 as candidate recipes (r2 and r3 are not considered because none of their
       # candidate systems are free).
       # During looping in scheduled_queued_recipes(), we complete
       # holds_deadlocking_resource_recipe, so that its resource (systemB)
       # is eligible to be the first candidate resource for
       # r4 (a candidate as it was released in between sessions, and
       # the first because it is owned by the creator of r4). r4 would
       # then be assigned this system and fail the assertion.

       # With this patch candidate systems cannot change once scheduled_queued_recipes()
       # is entered.
        with session.begin():
            user = data_setup.create_user()
            systemA = data_setup.create_system(lab_controller=self.lab_controller)
            # This gives systemB priority
            systemB = data_setup.create_system(owner=user, lab_controller=self.lab_controller)
            system_decoy = data_setup.create_system(lab_controller=self.lab_controller)
            system_spare = data_setup.create_system(lab_controller=self.lab_controller)

            holds_deadlocking_resource_recipe = data_setup.create_recipe()
            spare_recipe = data_setup.create_recipe()
            r1 = data_setup.create_recipe()
            r2 = data_setup.create_recipe()
            r3 = data_setup.create_recipe()
            r4 = data_setup.create_recipe()

            data_setup.create_job_for_recipes([holds_deadlocking_resource_recipe])
            data_setup.create_job_for_recipes([spare_recipe])
            j1 = data_setup.create_job_for_recipes([r1,r2])
            j2 = data_setup.create_job_for_recipes([r3,r4], owner=user)

            spare_recipe.systems[:] = [system_spare]
            r2.systems[:] = [systemB]
            r3.systems[:] = [systemA]
            r4.systems[:] = [systemB, system_decoy]

            # We need this to be the case so that we release
            # our resource at the correct time
            assert spare_recipe.id < r4.id

            data_setup.mark_recipe_running(holds_deadlocking_resource_recipe,
                system=systemB)
            data_setup.mark_recipe_running(r1, system=systemA)

            spare_recipe.process()
            spare_recipe.queue()

            r2.process()
            r2.queue()
            r3.process()
            r3.queue()
            r4.process()
            r4.queue()

        beakerd.update_dirty_jobs()

        engine = get_engine()
        SessionFactory = sessionmaker(bind=engine)
        session1 = SessionFactory()

        original_sqr = beakerd.schedule_queued_recipe
        def mock_sqr(recipe_id, guest_id=None):
            if recipe_id == spare_recipe.id:
                # We need to now release System B
                # to make sure it is not picked up
                with session1.begin():
                    complete_me = session1.query(Recipe).filter(Recipe.id ==
                        holds_deadlocking_resource_recipe.id).one()
                    data_setup.mark_recipe_complete(complete_me, only=True)
            else:
                pass
            original_sqr(recipe_id)

        try:
            beakerd.schedule_queued_recipe = mock_sqr
            beakerd.schedule_queued_recipes()
        finally:
            beakerd.schedule_queued_recipe = original_sqr
        r4 = Recipe.by_id(r4.id)
        r4.recipeset.job.update_status()
        self.assertTrue(r4.status, TaskStatus.scheduled)
        # This asserts that systemB was not found in the schedule_queued_recipe
        # loop. If it was it would have been picked due to owner priority
        self.assertEquals(r4.resource.system.fqdn, system_decoy.fqdn)

    def test_just_in_time_systems_multihost(self):
        with session.begin():
            systemA = data_setup.create_system(lab_controller=self.lab_controller)
            systemB = data_setup.create_system(lab_controller=self.lab_controller)
            r1 = data_setup.create_recipe()
            j1 = data_setup.create_job_for_recipes([r1])
            j1_id = j1.id
            r1.systems[:] = [systemA]
            r1.process()
            r1.queue()
            r1.recipeset.job.update_status()
            r1_id = r1.id

        beakerd.schedule_queued_recipes()

        with session.begin():
            r1 = Recipe.by_id(r1_id)
            data_setup.mark_recipe_running(r1)
            systemA = System.by_fqdn(systemA.fqdn, User.by_user_name('admin'))
            systemB = System.by_fqdn(systemB.fqdn, User.by_user_name('admin'))
            r2 = data_setup.create_recipe()
            r3 = data_setup.create_recipe()
            j2 = data_setup.create_job_for_recipes([r2,r3])
            j2_id = j2.id
            r2.systems[:] = [systemA]
            r3.systems[:] = [systemB]
            data_setup.mark_job_queued(j2)
            r2_id = r2.id
            r3_id = r3.id

        beakerd.schedule_queued_recipes()
        r2 = Recipe.by_id(r2_id)
        r3 = Recipe.by_id(r3_id)
        # First part of deadlock, systemB is scheduled, wait for systemA
        self.assertEqual(r2.status, TaskStatus.queued)
        self.assertEqual(r3.status, TaskStatus.scheduled)

        with session.begin():
            systemA = System.by_fqdn(systemA.fqdn, User.by_user_name('admin'))
            systemB = System.by_fqdn(systemB.fqdn, User.by_user_name('admin'))
            r4 = data_setup.create_recipe()
            r5 = data_setup.create_recipe()
            j3 = data_setup.create_job_for_recipes([r4,r5])
            r4_id = r4.id
            r5_id = r5.id
            j3_id = j3.id
            j3.recipesets[0].priority = TaskPriority.high
            r4.systems[:] = [systemA]
            r5.systems[:] = [systemB]
            j1 = Job.by_id(j1_id)
            data_setup.mark_job_complete(j1, only=True) # Release systemA
            j3 = Job.by_id(j3_id)
            data_setup.mark_job_queued(j3) # Queue higher priority recipes

        # Ensure j2 is clean
        with session.begin():
            j2 = Job.by_id(j2_id)
            j2.update_status()
        beakerd.schedule_queued_recipes()
        r2 = Recipe.by_id(r2_id)
        r3 = Recipe.by_id(r3_id)
        r4 = Recipe.by_id(r4_id)
        r5 = Recipe.by_id(r5_id)
        # Deadlock avoided due to prioritisation
        self.assertEqual(r4.status, TaskStatus.queued)
        self.assertEqual(r5.status, TaskStatus.queued)
        self.assertEqual(r2.status, TaskStatus.scheduled)
        self.assertEqual(r3.status, TaskStatus.scheduled)

    def test_loaned_machine_can_be_scheduled(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(status=u'Automated',
                    shared=False, lab_controller=self.lab_controller)
            # User is denied by the policy, but system is loaned to the user
            self.assertFalse(system.custom_access_policy.grants(user,
                       SystemPermission.reserve))
            system.loaned = user
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)

    def test_reservations_are_created(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated',
                    shared=True, lab_controller=self.lab_controller)
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            system = System.query.get(system.id)
            user = User.query.get(user.user_id)
            self.assertEqual(job.status, TaskStatus.scheduled)
            self.assertEqual(system.reservations[0].type, u'recipe')
            self.assertEqual(system.reservations[0].user, user)
            assert_datetime_within(system.reservations[0].start_time,
                    tolerance=datetime.timedelta(seconds=60),
                    reference=datetime.datetime.utcnow())
            self.assert_(system.reservations[0].finish_time is None)
            assert_durations_not_overlapping(system.reservations)

    def test_empty_and_element(self):
        with session.begin():
            user = data_setup.create_user()
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    u'<hostRequires><and></and></hostRequires>')

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)

    def test_or_lab_controller(self):
        with session.begin():
            user = data_setup.create_user()
            lc1 = data_setup.create_labcontroller(u'test_or_labcontroller.lab1')
            lc2 = data_setup.create_labcontroller(u'test_or_labcontroller.lab2')
            lc3 = data_setup.create_labcontroller(u'test_or_labcontroller.lab3')
            system1 = data_setup.create_system(arch=u'i386', shared=True)
            system1.lab_controller = lc1
            system2 = data_setup.create_system(arch=u'i386', shared=True)
            system2.lab_controller = lc2
            system3 = data_setup.create_system(arch=u'i386', shared=True)
            system3.lab_controller = lc3
            distro_tree = data_setup.create_distro_tree(lab_controllers=[lc1, lc2, lc3])
            job = data_setup.create_job(owner=user, distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                   <hostRequires>
                    <or>
                     <hostlabcontroller op="=" value="test_or_labcontroller.lab1"/>
                     <hostlabcontroller op="=" value="test_or_labcontroller.lab2"/>
                    </or>
                   </hostRequires>
                   """)
            session.flush()
            job_id = job.id
            system1_id = system1.id
            system2_id = system2.id
            system3_id = system3.id

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            system1 = System.query.get(system1_id)
            system2 = System.query.get(system2_id)
            system3 = System.query.get(system3_id)
            self.assertEqual(job.status, TaskStatus.processed)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(len(candidate_systems), 2)
            self.assert_(system1 in candidate_systems)
            self.assert_(system2 in candidate_systems)
            self.assert_(system3 not in candidate_systems)

    def check_user_cannot_run_job_on_system(self, user, system):
        """
        Asserts that the given user is not allowed to run a job against the 
        given system, i.e. that it aborts due to no matching systems.
        """
        with session.begin():
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.aborted)
        return job.id

    def check_user_can_run_job_on_system(self, user, system):
        """
        Asserts that the given user *is* allowed to run a job against the given 
        system, i.e. that it does not abort due to no matching systems. Inverse 
        of the method above.
        """
        with session.begin():
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)
        return job.id

    def test_nonshared_system_not_owner(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False, owner=data_setup.create_user())
        self.check_user_cannot_run_job_on_system(user, system)

    def test_nonshared_system_owner(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False, owner=user)
        self.check_user_can_run_job_on_system(user, system)

    def test_nonshared_system_admin(self):
        with session.begin():
            admin = data_setup.create_admin()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
        self.check_user_cannot_run_job_on_system(admin, system)

    def test_shared_system_not_owner(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
        self.check_user_can_run_job_on_system(user, system)

    def test_shared_system_admin(self):
        with session.begin():
            admin = data_setup.create_admin()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
        self.check_user_can_run_job_on_system(admin, system)

    def test_shared_group_system_with_user_not_in_group(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        self.check_user_cannot_run_job_on_system(user, system)

    def test_shared_group_system_with_user_in_group(self):
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user()
            user.groups.append(group)
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        self.check_user_can_run_job_on_system(user, system)

    def test_shared_group_system_with_admin_not_in_group(self):
        with session.begin():
            admin = data_setup.create_admin()
            group = data_setup.create_group()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        self.check_user_cannot_run_job_on_system(admin, system)

    def test_shared_group_system_with_admin_in_group(self):
        with session.begin():
            group = data_setup.create_group()
            admin = data_setup.create_admin()
            admin.groups.append(group)
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        self.check_user_can_run_job_on_system(admin, system)

    def test_loaned_system_with_admin(self):
        with session.begin():
            loanee = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, loaned=loanee)
            admin = data_setup.create_admin()
        job_id = self.check_user_can_run_job_on_system(admin, system)
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
            system = System.query.get(system.id)
            self.assertEqual(system.user, None)

    def test_loaned_system_with_loanee(self):
        with session.begin():
            loanee = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, loaned=loanee)
        job_id = self.check_user_can_run_job_on_system(loanee, system)
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.scheduled)
            system = System.query.get(system.id)
            self.assertEqual(system.user.user_id, loanee.user_id)

    def test_loaned_system_with_not_loanee(self):
        with session.begin():
            loanee = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, loaned=loanee)
            user = data_setup.create_user()
        job_id = self.check_user_can_run_job_on_system(user, system)
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
            system = System.query.get(system.id)
            self.assertEqual(system.user, None)

    def test_loaned_system_with_owner(self):
        with session.begin():
            loanee = data_setup.create_user()
            owner = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, owner=owner, loaned=loanee)
        # owner of the system has access, when the
        # loan is returned their job will be able to run.
        job_id = self.check_user_can_run_job_on_system(owner, system)
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
            system = System.query.get(system.id)
            self.assertEqual(system.user, None)

    def test_disabled_lab_controller(self):
        with session.begin():
            system = data_setup.create_system(status=u'Automated', shared=True,
                    lab_controller=self.lab_controller)
            job = data_setup.create_job()
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
            self.lab_controller.disabled = True
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            recipeset = RecipeSet.by_id(job.recipesets[0].id)
            self.assertEquals(recipeset.status, TaskStatus.queued)
        # now re-enable it
        with session.begin():
            LabController.query.get(self.lab_controller.id).disabled = False
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            recipeset = RecipeSet.by_id(job.recipesets[0].id)
            self.assertEquals(recipeset.status, TaskStatus.scheduled)

    def test_fail_harness_repo(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated', shared=True,
                    lab_controller=self.lab_controller)
            job = data_setup.create_job(owner=user)
            recipe = job.recipesets[0].recipes[0]
            recipe._host_requires = (
                    u'<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        harness_dir = '%s/%s' % (recipe.harnesspath, \
            recipe.distro_tree.distro.osversion.osmajor)
        try:
            if os.path.exists(harness_dir):
                os.rmdir(harness_dir)
            beakerd.process_new_recipes()
            beakerd.update_dirty_jobs()
            beakerd.queue_processed_recipesets()
            beakerd.update_dirty_jobs()
            beakerd.schedule_queued_recipes()
            beakerd.update_dirty_jobs()
            beakerd.provision_scheduled_recipesets()
            beakerd.update_dirty_jobs()
            with session.begin():
                job = Job.by_id(job.id)
                self.assertEqual(job.status, TaskStatus.aborted)
        finally:
            if not os.path.exists(harness_dir):
                os.mkdir(harness_dir)
    
    def test_success_harness_repo(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated',
                    shared=True, lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            job = data_setup.create_job(owner=user, distro_tree=distro_tree)
            recipe = job.recipesets[0].recipes[0]
            recipe._host_requires = (
                    '<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        harness_dir = '%s/%s' % (recipe.harnesspath, \
            recipe.distro_tree.distro.osversion.osmajor)

        if not os.path.exists(harness_dir):
            os.mkdir(harness_dir)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.by_id(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)

    def test_single_processor_priority(self):
        with session.begin():
            user = data_setup.create_user()
            system_two_proc_owner = data_setup.create_system(
                lab_controller=self.lab_controller, owner=user, cpu=Cpu(processors=2))
            system_one_proc_owner = data_setup.create_system(
                lab_controller=self.lab_controller, owner=user, cpu=Cpu(processors=1))
            system_one_proc_kvm = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=1), hypervisor=u'KVM')
            system_two_proc = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=2))
            system_one_proc = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=1))
            system_no_proc = data_setup.create_system(
                lab_controller=self.lab_controller)
            # Just in case we start adding CPUs by default to systems...
            system_no_proc.cpu = None

            recipe1 = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe1])
            job.owner = user
            recipe1.process()
            recipe1.queue()
            # Some fodder machines in here as well
            recipe1.systems[:] = [system_no_proc, system_one_proc,
                system_one_proc_owner, system_two_proc, system_two_proc_owner]
        beakerd.schedule_queued_recipe(recipe1.id)
        session.refresh(recipe1)
        # Test 2 proc > 1 proc within the owners
        self.assertEqual(recipe1.resource.system, system_two_proc_owner)

        # Test that non group, non owner single processor sorting works
        # and that only bare metal machines are considered in the single
        # processor ordering.
        with session.begin():
            recipe2 = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe2])
            recipe2.process()
            recipe2.queue()
            recipe2.systems[:] = [system_one_proc, system_two_proc,
                system_one_proc_kvm]
        beakerd.schedule_queued_recipe(recipe2.id)
        self.assertNotEqual(recipe2.resource.system, system_one_proc)

        # Test that group owner priority higher than dual processor
        with session.begin():
            recipe3 = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe3])
            system_two_proc_again = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=2))
            job.owner = user
            recipe3.process()
            recipe3.queue()
            recipe3.systems[:] = [system_two_proc_again, system_one_proc_owner]
        beakerd.schedule_queued_recipe(recipe3.id)
        self.assertEqual(recipe3.resource.system, system_one_proc_owner)

    def test_successful_recipe_start(self):
        with session.begin():
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            job = data_setup.create_job(distro_tree=distro_tree)
            recipe = job.recipesets[0].recipes[0]
            recipe._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        # Sanity check the test setup
        rpm_name = self.rpm_name
        self.assert_(os.path.exists(Task.get_rpm_path(rpm_name)))

        # Start the recipe processing
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()

        # Scheduled recipe sets should have a recipe specific task repo
        recipe_repo = os.path.join(recipe.repopath, str(recipe.id))
        recipe_metadata = os.path.join(recipe_repo, 'repodata')
        self.assert_(os.path.exists(recipe_metadata))
        recipe_task_rpm = os.path.join(recipe_repo, rpm_name)
        self.assert_(os.path.exists(recipe_task_rpm))

        # And then continue on to provision the system
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            self.assertEqual(system.command_queue[0].action, 'reboot')
            self.assertEqual(system.command_queue[1].action, 'configure_netboot')
            self.assertEqual(system.command_queue[2].action, 'clear_logs')

    # https://bugzilla.redhat.com/show_bug.cgi?id=880852
    def test_recipe_no_longer_has_access(self):
        with session.begin():
            group = data_setup.create_group()
            job_owner = data_setup.create_user()
            job_owner.groups.append(group)
            system1 = data_setup.create_system(fqdn='no-longer-has-access1.invalid',
                    lab_controller=self.lab_controller)
            system1.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
            system1.groups.append(group)
            system2 = data_setup.create_system(shared=True,
                    fqdn='no-longer-has-access2.invalid',
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree()
            job = data_setup.create_job(owner=job_owner, distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = u"""
                <hostRequires>
                    <or>
                        <hostname op="=" value="no-longer-has-access1.invalid" />
                        <hostname op="=" value="no-longer-has-access2.invalid" />
                    </or>
                </hostRequires>
                """
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            system1 = System.query.get(system1.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.queued)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(candidate_systems, [system1, system2])
            # now remove access to system1
            system1.custom_access_policy.rules[:] = []
        # first iteration: "recipe no longer has access"
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.queued)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(candidate_systems, [system2])
        # second iteration: system2 is picked instead
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.scheduled)
            picked_system = job.recipesets[0].recipes[0].resource.system
            self.assertEqual(picked_system, system2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=826379
    def test_recipe_install_options_can_remove_system_options(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            system.provisions[distro_tree.arch] = Provision(arch=distro_tree.arch,
                    kernel_options='console=ttyS0 vnc')
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0].kernel_options = u'!vnc'
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            self.assertEqual(system.command_queue[1].action, 'configure_netboot')
            self.assert_('vnc' not in system.command_queue[1].kernel_options)

    def test_order_by(self):
        controller = Jobs()
        with session.begin():
            lab_controller = data_setup.create_labcontroller()

        with session.begin():
            distro_tree = data_setup.create_distro_tree()
            user = data_setup.create_admin()
            for x in range(0,3):
                data_setup.create_system(shared=True,
                        owner=user,
                        lab_controller=lab_controller)

        xmljob = XmlJob(xmltramp.parse("""
<job retention_tag="scratch">
	<whiteboard>
		
	</whiteboard>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
</job>
                 """ % dict(labcontroller = lab_controller.fqdn,
                            family        = distro_tree.distro.osversion.osmajor,
                            variant       = distro_tree.variant,
                            name          = distro_tree.distro.name,
                            arch          = distro_tree.arch)))

        with session.begin():
            job = controller.process_xmljob(xmljob, user)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_queued_recipes()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            for x in range(0,2):
                self.assertEqual(job.recipesets[x].recipes[0].status,
                                 TaskStatus.queued)
            for x in range(2,3):
                self.assertEqual(job.recipesets[x].recipes[0].status,
                                 TaskStatus.scheduled)
            for x in range(5,3):
                self.assertEqual(job.recipesets[x].recipes[0].status,
                                 TaskStatus.queued)

class FakeMetrics():
    def __init__(self):
        self.calls = []
    def measure(self, *args):
        self.calls.append(args)

class TestBeakerdMetrics(unittest.TestCase):

    def setUp(self):
        self.original_metrics = beakerd.metrics
        beakerd.metrics = FakeMetrics()
        self.mail_capture = MailCaptureThread()
        self.mail_capture.start()
        session.begin()
        # Other tests might have left behind systems and running recipes,
        # so we remove or cancel them all so they don't pollute our metrics
        manually_reserved = System.query.filter(System.open_reservation != None)
        for system in manually_reserved:
            data_setup.unreserve_manual(system)
        systems = System.query.filter(System.status != SystemStatus.removed)
        for system in systems:
            system.status = SystemStatus.removed
        running = Recipe.query.filter(not_(Recipe.status.in_(
                [s for s in TaskStatus if s.finished])))
        for recipe in running:
            recipe.cancel()
            recipe.recipeset.job.update_status()

    def tearDown(self):
        session.rollback()
        self.mail_capture.stop()
        beakerd.metrics = self.original_metrics

    def test_system_count_metrics(self):
        gauges = [
            'gauges.systems_recipe',
            'gauges.systems_manual',
            'gauges.systems_idle_broken',
            'gauges.systems_idle_manual',
            'gauges.systems_idle_automated',
        ]
        categories = [
            'all',
            'shared',
            'by_arch.x86_64',
            'by_arch.i386',
            'by_arch.ppc',
            'by_arch.ppc64',
            'by_lab.checkmetrics_invalid_com',
        ]
        lc = data_setup.create_labcontroller(fqdn=u"checkmetrics.invalid.com")
        expected = dict(("%s.%s" % (g, c), 0)
                            for g in gauges for c in categories)
        for arch in u"i386 x86_64 ppc ppc64".split():
            data_setup.create_system(lab_controller=lc, arch=arch)
            data_setup.create_system(lab_controller=lc, arch=arch,
                                     status=SystemStatus.removed)
            categories = ['all', 'shared', 'by_lab.checkmetrics_invalid_com',
                          'by_arch.%s' % arch]
            for category in categories:
                key = 'gauges.systems_idle_automated.%s' % category
                expected[key] += 1
        # Ensure the test can cope with other systems showing
        # up as "idle_removed" in the metrics.
        lc = data_setup.create_labcontroller(fqdn=u"emptylab.invalid.com")
        data_setup.create_system(lab_controller=lc,
                                  status=SystemStatus.removed)
        session.flush()
        beakerd.system_count_metrics()
        # We need to split out unknown lab metrics, which we may inherit
        # from other tests which left systems in the database
        all_labs = {}
        known_metrics = {}
        other_labs = {}
        for k, v in beakerd.metrics.calls:
            all_labs[k] = v
            if k in expected:
                known_metrics[k] = v
            else:
                other_labs[k] = v
        self.assertEqual(set(known_metrics), set(expected))
        for k, v in known_metrics.iteritems():
            self.assertEqual((k, v), (k, expected[k]))
        for k, v in other_labs.iteritems():
            self.assertEqual((k, v), (k, 0))

    def test_recipe_count_metrics(self):
        gauges = [
            'gauges.recipes_scheduled',
            'gauges.recipes_running',
            'gauges.recipes_waiting',
            'gauges.recipes_processed',
            'gauges.recipes_new',
            'gauges.recipes_queued',
        ]
        categories = [
            'all',
            'dynamic_virt_possible',
            'by_arch.x86_64',
            'by_arch.i386',
            'by_arch.ppc',
            'by_arch.ppc64',
        ]
        expected = dict(("%s.%s" % (g, c), 0)
                            for g in gauges for c in categories)
        recipes = []
        for arch in u"i386 x86_64 ppc ppc64".split():
            dt = data_setup.create_distro_tree(arch=arch)
            job = data_setup.create_job(num_guestrecipes=1, distro_tree=dt)
            recipe = job.recipesets[0].recipes[0]
            recipes.append(recipe)
            categories = ['all', 'dynamic_virt_possible',
                          'by_arch.%s' % arch]
            for category in categories:
                key = 'gauges.recipes_new.%s' % category
                expected[key] += 1
        session.flush()
        beakerd.recipe_count_metrics()
        actual = dict(beakerd.metrics.calls)
        self.assertEqual(set(actual), set(expected))
        for k, v in actual.iteritems():
            self.assertEqual((k, v), (k, expected[k]))
        # Processing the recipes should set their virt status correctly
        for category in categories:
            new = 'gauges.recipes_new.%s' % category
            processed = 'gauges.recipes_processed.%s' % category
            if category != 'dynamic_virt_possible':
                expected[new], expected[processed] = 0, expected[new]
            else:
                # Possible virt candidates: i386, x86_64
                expected[new], expected[processed] = 0, 2
        for recipe in recipes:
            beakerd.process_new_recipe(recipe.id)
        beakerd.metrics.calls[:] = []
        beakerd.recipe_count_metrics()
        actual = dict(beakerd.metrics.calls)
