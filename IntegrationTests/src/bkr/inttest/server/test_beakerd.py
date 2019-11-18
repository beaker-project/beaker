
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import os
import threading
import shutil
import logging
import pkg_resources
from mock import patch
import bkr

from bkr.server.model import TaskStatus, Job, System, User, \
        Group, SystemStatus, SystemActivity, Recipe, Cpu, LabController, \
        Provision, TaskPriority, RecipeSet, RecipeTaskResult, Task, SystemPermission,\
        MachineRecipe, GuestRecipe, LabControllerDistroTree, DistroTree, \
        TaskResult, Command, CommandStatus, GroupMembershipType, \
        RecipeVirtStatus, Arch
from bkr.server.installopts import InstallOptions
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import not_
from turbogears import config
from turbogears.database import session, get_engine
import lxml.etree
from bkr.inttest import data_setup, fix_beakerd_repodata_perms, DatabaseTestCase
from bkr.inttest.assertions import assert_datetime_within, \
        assert_durations_not_overlapping, wait_for_condition
from bkr.server.tools import beakerd
from bkr.server.jobs import Jobs
from bkr.server import dynamic_virt
from bkr.server.model import OSMajor
from bkr.server.model.installation import RenderedKickstart
from bkr.inttest.assertions import assert_datetime_within
from unittest import SkipTest

log = logging.getLogger(__name__)

class TestBeakerd(DatabaseTestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            # Other tests might have left behind recipes which will interfere
            # with mocking behaviour in these tests. Remove and cancel them so
            # they don't interfere.
            running = Recipe.query.filter(not_(Recipe.status.in_(
                [s for s in TaskStatus if s.finished])))
            for recipe in running:
                recipe.recipeset.cancel()
                recipe.recipeset.job.update_status()
        self.task_id, self.rpm_name = self.add_example_task()

    def tearDown(self):
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
                    pkg_resources.resource_filename('bkr.inttest.server', 'task-rpms/empty.rpm'),
                    rpm_path)
            return task.id, task.rpm

    def disable_example_task(self, task_id):
        with session.begin():
            task = Task.by_id(task_id)
            task.disable()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1635309
    def test_dont_abort_custom_distro(self):
        with session.begin():
            system = data_setup. \
                create_system(lab_controller=self.lab_controller)
            r1 = data_setup.create_recipe(custom_distro=True)
            r2 = data_setup.create_recipe(custom_distro=True)
            j1 = data_setup.create_job_for_recipes([r1])
            j2 = data_setup.create_job_for_recipes([r2])

            r1.systems[:] = [system]
            r2.systems[:] = [system]
            data_setup.mark_job_installing(j1)

        with session.begin():
            data_setup.mark_job_queued(j2)

        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            j2 = Job.by_id(j2.id)
            self.assertTrue(j1.status is TaskStatus.installing, j1.status)
            self.assertTrue(j2.status is TaskStatus.queued, j2.status)
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            j2 = Job.by_id(j2.id)
            self.assertTrue(j1.status is TaskStatus.installing, j1.status)
            self.assertTrue(j2.status is TaskStatus.queued, j2.status)

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_failed_recipe_started_before_upgrade_finished_after_upgrade_does_not_fail(self):
        with session.begin():
            job = data_setup.create_running_job()
            job_id = job.id

        self.assertEqual(job.status, TaskStatus.running)

        with session.begin():
            job = Job.by_id(job_id)
            recipe = job.recipesets[0].recipes[0]
            # if recipe was run before the upgrade, it wont have some installation table columns
            recipe.installation.arch = None
            recipe.installation.distro_name = None
            recipe.installation.variant = None
            recipe.installation.osmajor = None
            recipe.installation.osminor = None
            data_setup.mark_recipe_tasks_finished(recipe, only=True, result=TaskResult.fail)

        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.by_id(job_id)
            self.assertEqual(job.status, TaskStatus.completed)

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
        j1_id = j1.id
        with session.begin():
            j1 = Job.by_id(j1_id)
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
        j1_id = j1.id
        dt_for_guest_id = dt_for_guest.id
        with session.begin():
            j1 = Job.by_id(j1_id)
            self.assertEquals(j1.status, TaskStatus.queued, j1.status)
            dt_for_guest = DistroTree.by_id(dt_for_guest_id)
            dt_for_guest.lab_controller_assocs.append(
                LabControllerDistroTree(lab_controller=host_lab_controller,
                    url=u'http://whatevs.com'))
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        with session.begin():
            j1 = Job.by_id(j1_id)
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
            r1._host_requires = ("""<hostRequires><or>
                    <hostname op="=" value="%s" />
                    <hostname op="=" value="%s" />
                </or></hostRequires>""" % (system_A1, system_B1))
            r2 = data_setup.create_recipe()
            r2._host_requires = ("""<hostRequires><or>
                    <hostname op="=" value="%s" />
                    <hostname op="=" value="%s" />
                </or></hostRequires>""" % (system_A2, system_B2))
            job = data_setup.create_job_for_recipes([r1,r2])
            # Ensure both recipes have a free system, but in different labs
            user = data_setup.create_user()
            system_A1.user = user
            system_B2.user = user

        # Turn the crank
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()

        # Check only the first recipe is scheduled at this point
        job_id = job.id
        r1_id = r1.id
        r2_id = r2.id
        system_B2_id = system_B2.id
        with session.begin():
            job = Job.by_id(job_id)
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

        # Check the job is scheduled once the relevant system becomes free
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.by_id(job_id)
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
            r1.virt_status = RecipeVirtStatus.precluded
            r1.systems[:] = [system]
            data_setup.mark_job_running(j2, system=system)

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
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        session.expunge_all()
        # We should still be queued here.
        with session.begin():
            j1 = Job.by_id(j1.id)
            self.assertTrue(j1.status is TaskStatus.queued, j1.status)
            self.assertEquals(j1.recipesets[0].recipes[0].systems, [])
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            self.assertTrue(j1.status is TaskStatus.aborted, j1.status)

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_dead_recipe_with_custom_distro_abort_does_not_fail(self):
        with session.begin():
            system = data_setup. \
                create_system(lab_controller=self.lab_controller)
            r1 = data_setup.create_recipe(custom_distro=True)
            j1 = data_setup.create_job_for_recipes([r1])

            data_setup.mark_job_queued(j1)
            r1.virt_status = RecipeVirtStatus.precluded
            r1.systems[:] = [system]

        # Mark system broken and cancel the job
        with session.begin():
            system.status = SystemStatus.broken

        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            self.assertTrue(j1.status is TaskStatus.queued)
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        session.expunge_all()
        with session.begin():
            j1 = Job.by_id(j1.id)
            self.assertTrue(j1.status is TaskStatus.aborted, j1.status)

    # https://bugzilla.redhat.com/show_bug.cgi?id=889065
    # https://bugzilla.redhat.com/show_bug.cgi?id=1470959
    def test_just_in_time_systems_multihost(self):
        with session.begin():
            systemA = data_setup.create_system(lab_controller=self.lab_controller)
            systemB = data_setup.create_system(lab_controller=self.lab_controller)
            r1 = data_setup.create_recipe()
            j1 = data_setup.create_job_for_recipes([r1])
            j1_id = j1.id
            data_setup.mark_recipe_running(r1, system=systemA)
            systemA = System.by_fqdn(systemA.fqdn, User.by_user_name(u'admin'))
            systemB = System.by_fqdn(systemB.fqdn, User.by_user_name(u'admin'))
            r2 = data_setup.create_recipe()
            r2._host_requires = u'<hostRequires force="%s"/>' % systemA.fqdn
            r3 = data_setup.create_recipe()
            r3._host_requires = u'<hostRequires force="%s"/>' % systemB.fqdn
            j2 = data_setup.create_job_for_recipes([r2,r3])
            j2_id = j2.id
            r2_id = r2.id
            r3_id = r3.id

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        r2 = Recipe.by_id(r2_id)
        r3 = Recipe.by_id(r3_id)
        # First part of deadlock, systemB is scheduled, wait for systemA
        self.assertEqual(r2.status, TaskStatus.queued)
        self.assertEqual(r3.status, TaskStatus.scheduled)

        with session.begin():
            systemA = System.by_fqdn(systemA.fqdn, User.by_user_name(u'admin'))
            systemB = System.by_fqdn(systemB.fqdn, User.by_user_name(u'admin'))
            r4 = data_setup.create_recipe()
            r4._host_requires = u'<hostRequires force="%s"/>' % systemA.fqdn
            r5 = data_setup.create_recipe()
            r5._host_requires = u'<hostRequires force="%s"/>' % systemB.fqdn
            j3 = data_setup.create_job_for_recipes([r4,r5])
            r4_id = r4.id
            r5_id = r5.id
            j3_id = j3.id
            j3.recipesets[0].priority = TaskPriority.high
            j1 = Job.by_id(j1_id)
            data_setup.mark_job_complete(j1, only=True) # Release systemA
            j3 = Job.by_id(j3_id)
            data_setup.mark_job_queued(j3) # Queue higher priority recipes
            # Make j2 dirty. This can happen in the real scheduler if j2
            # contains *other* unrelated recipe sets which are already running
            # and receiving updates from the harness.
            # But it shouldn't stop r2 from being scheduled.
            j2 = Job.by_id(j2_id)
            j2._mark_dirty()

        beakerd.schedule_pending_systems()
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
                    u'<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)

    def test_like_named_machine(self):

        with session.begin():
            user = data_setup.create_user()
            system1 = data_setup.create_system(status=u'Automated',
                    fqdn='boston1.redhat.com',
                    lab_controller=self.lab_controller)
            # Notice name change s/bos/boz/ in next system create
            system2 = data_setup.create_system(status=u'Automated',
                    fqdn='bozton2.redhat.com',
                    lab_controller=self.lab_controller)
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    u'<hostRequires><hostname op="like" value="%bos%"/></hostRequires>')

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)
            self.assertEqual(len(job.recipesets[0].recipes[0].systems), 1)
            system = job.recipesets[0].recipes[0].systems[0]
            self.assertEqual(system.fqdn, u'boston1.redhat.com')

    def test_reservations_are_created(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated',
                    shared=True, lab_controller=self.lab_controller)
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    u'<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
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
            system = data_setup.create_system(owner=user, status=u'Automated',
                    shared=True, lab_controller=self.lab_controller)
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
            lc1 = data_setup.create_labcontroller()
            lc2 = data_setup.create_labcontroller()
            lc3 = data_setup.create_labcontroller()
            system1 = data_setup.create_system(arch=u'i386', shared=True, lab_controller=lc1)
            system2 = data_setup.create_system(arch=u'i386', shared=True, lab_controller=lc2)
            system3 = data_setup.create_system(arch=u'i386', shared=True, lab_controller=lc3)
            distro_tree = data_setup.create_distro_tree(lab_controllers=[lc1, lc2, lc3])
            job = data_setup.create_job(owner=user, distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                   <hostRequires>
                    <or>
                     <hostlabcontroller op="=" value="%s"/>
                     <hostlabcontroller op="=" value="%s"/>
                    </or>
                   </hostRequires>
                   """ % (lc1.fqdn, lc2.fqdn))
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
            group.add_member(user)
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        self.check_user_can_run_job_on_system(user, system)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_shared_group_system_with_user_in_inverted_group(self):
        with session.begin():
            group = data_setup.create_group(membership_type=GroupMembershipType.inverted)
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                permission=SystemPermission.reserve, group=group)
        self.check_user_can_run_job_on_system(user, system)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1220610
    def test_shared_group_system_with_user_excluded_from_inverted_group(self):
        with session.begin():
            group = data_setup.create_group(membership_type=GroupMembershipType.inverted)
            user = data_setup.create_user()
            group.exclude_user(user)
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
            system.custom_access_policy.add_rule(
                permission=SystemPermission.reserve, group=group)
        self.check_user_cannot_run_job_on_system(user, system)

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
            group.add_member(admin)
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
        beakerd.schedule_pending_systems()
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
        beakerd.schedule_pending_systems()
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
        beakerd.schedule_pending_systems()
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
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        with session.begin():
            recipeset = RecipeSet.by_id(job.recipesets[0].id)
            self.assertEquals(recipeset.status, TaskStatus.queued)
        # now re-enable it
        with session.begin():
            LabController.query.get(self.lab_controller.id).disabled = False
        beakerd.schedule_pending_systems()
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
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
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
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.by_id(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1005865
    def test_harness_repo_not_required_when_using_alternative_harness(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated', shared=True,
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            job = data_setup.create_job(owner=user, distro_tree=distro_tree)
            recipe = job.recipesets[0].recipes[0]
            recipe.ks_meta = "harness='myharness' no_default_harness_repo"
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
            beakerd.provision_scheduled_recipesets()
            beakerd.update_dirty_jobs()
            with session.begin():
                job = Job.by_id(job.id)
                self.assertEqual(job.status, TaskStatus.waiting)
        finally:
            if not os.path.exists(harness_dir):
                os.mkdir(harness_dir)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1157348
    def test_harness_repo_not_required_contained_harness(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'MyAwesomeNewLinux',
                                                        harness_dir=False)
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            recipe.ks_meta = "contained_harness no_default_harness_repo"
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe)
        # The test is just checking that recipe.provision() can be called
        # without exploding and aborting the recipe due to missing harness repo
        # directory.

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
            recipe1._host_requires = (
                '<hostRequires><labcontroller value="%s"/></hostRequires>'
                % self.lab_controller.fqdn)
            job1 = data_setup.create_job_for_recipes([recipe1], owner=user)
            recipe1_id = recipe1.id

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            recipe1 = Recipe.by_id(recipe1_id)
            self.assertEquals(recipe1.status, TaskStatus.scheduled)
            # 2-processor machine beloning to the job owner should be preferred
            self.assertEquals(recipe1.resource.system.fqdn, system_two_proc_owner.fqdn)

        # Test that non group, non owner single processor sorting works
        # and that only bare metal machines are considered in the single
        # processor ordering.
        with session.begin():
            recipe2 = data_setup.create_recipe()
            recipe2._host_requires = '<hostRequires><cpu_count op="=" value="1"/></hostRequires>'
            job2 = data_setup.create_job_for_recipes([recipe2])
            recipe2_id = recipe2.id
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            recipe2 = Recipe.by_id(recipe2_id)
            self.assertEquals(recipe2.status, TaskStatus.scheduled)
            self.assertEquals(recipe2.resource.system.fqdn, system_one_proc_kvm.fqdn)

        # Test that group owner priority higher than dual processor
        with session.begin():
            recipe3 = data_setup.create_recipe()
            recipe3._host_requires = (
                '<hostRequires><labcontroller value="%s"/></hostRequires>'
                % self.lab_controller.fqdn)
            job = data_setup.create_job_for_recipes([recipe3], owner=user)
            recipe3_id = recipe3.id
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            recipe3 = Recipe.by_id(recipe3_id)
            self.assertEquals(recipe3.status, TaskStatus.scheduled)
            self.assertEquals(recipe3.resource.system.fqdn, system_one_proc_owner.fqdn)

    def test_successful_recipe_start(self):
        with session.begin():
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
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

        # Scheduled recipe sets should have a recipe specific task repo
        recipe_repo = os.path.join(recipe.repopath, str(recipe.id))
        recipe_metadata = os.path.join(recipe_repo, 'repodata')
        self.assert_(os.path.exists(recipe_metadata))
        recipe_task_rpm = os.path.join(recipe_repo, rpm_name)
        self.assert_(os.path.exists(recipe_task_rpm))

        # And then continue on to provision the system
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            self.assertEqual(system.command_queue[0].action, 'on')
            self.assertEqual(system.command_queue[1].action, 'off')
            self.assertEqual(system.command_queue[2].action, 'configure_netboot')
            self.assertEqual(system.command_queue[3].action, 'clear_logs')

    def test_task_versions_are_recorded(self):
        with session.begin():
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            task = Task.by_id(self.task_id)
            recipe = data_setup.create_recipe(distro_tree=distro_tree,
                    task_list=[task])
            recipe._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)
            job = data_setup.create_job_for_recipes([recipe])

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEquals(job.recipesets[0].recipes[0].tasks[0].version,
                    task.version)

    # https://bugzilla.redhat.com/show_bug.cgi?id=880852
    def test_recipe_no_longer_has_access(self):
        with session.begin():
            job_owner = data_setup.create_user()
            # system1 is added to a pool to make sure system1 is picked first
            # before system2
            # See: bkr.server.model.inventory:scheduler_ordering
            system1 = data_setup.create_system(shared=True,
                                               fqdn=u'no-longer-has-access1.invalid',
                                               lab_controller=self.lab_controller)
            system1.pools.append(data_setup.create_system_pool())
            system2 = data_setup.create_system(shared=True,
                    fqdn=u'no-longer-has-access2.invalid',
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
            # Both system1 and system2 are initially lent to someone else.
            system1.loaned = system2.loaned = data_setup.create_user()
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
            # now change acess policy of system1 so that none has any permission
            # and system1 is not picked up as one of the systems in
            # candidate_systems in schedule_pending_systems()
            system1.custom_access_policy.rules[:] = []
            system1.loaned = None
        # first iteration: "recipe no longer has access"
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.queued)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(candidate_systems, [system2])
            # free up system2
            system2.loaned = None
        # second iteration: system2 is picked instead
        beakerd.schedule_pending_systems()
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
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
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
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            self.assertNotIn('vnc',
                    job.recipesets[0].recipes[0].installation.kernel_options)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1067924
    def test_kernel_options_are_not_quoted(self):
        # URL contains ~ which is quoted by pipes.quote
        bad_arg = 'inst.updates=http://people.redhat.com/~dlehman/updates-1054806.1.img'
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora20')
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0].kernel_options = u'%s' % bad_arg
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            self.assertIn(bad_arg,
                    job.recipesets[0].recipes[0].installation.kernel_options)

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

        xmljob = lxml.etree.fromstring("""
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
                            arch          = distro_tree.arch))

        with session.begin():
            job = controller.process_xmljob(xmljob, user)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
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

    #https://bugzilla.redhat.com/show_bug.cgi?id=851354
    def test_provision_broken_manual_systems(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            system1 = data_setup.create_system(shared=True,
                                               lab_controller=self.lab_controller)
            system1.status = SystemStatus.broken
            system2 = data_setup.create_system(shared=True,
                                               lab_controller=self.lab_controller)
            system2.status = SystemStatus.manual
            lc = data_setup.create_labcontroller()
            system3 = data_setup.create_system(shared=True, lab_controller=lc)
            system3.status = SystemStatus.broken

            job1 = data_setup.create_job(distro_tree=distro_tree)
            job2 = data_setup.create_job(distro_tree=distro_tree)
            job3 = data_setup.create_job(distro_tree=distro_tree)

            host_requires = u'<hostRequires force="{0}" />'
            job1.recipesets[0].recipes[0]._host_requires = host_requires.format(system1.fqdn)
            job2.recipesets[0].recipes[0]._host_requires = host_requires.format(system2.fqdn)
            job3.recipesets[0].recipes[0]._host_requires = host_requires.format(system3.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job1.id)
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.scheduled)
            job = Job.query.get(job2.id)
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.scheduled)
            # this job should be aborted because the distro is not available
            # on the LC to which the system is attached
            job = Job.query.get(job3.id)
            recipetask_id = job.recipesets[0].recipes[0].tasks[0].id
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.aborted)
            result = RecipeTaskResult.query.filter(
                RecipeTaskResult.recipe_task_id == recipetask_id).one()
            self.assertEquals(result.log,
                              'Recipe ID %s does not match any systems' %
                              job.recipesets[0].recipes[0].id)

    #https://bugzilla.redhat.com/show_bug.cgi?id=851354
    def test_force_system_access_policy_obeyed(self):
        with session.begin():
            user1 = data_setup.create_user()
            user2 = data_setup.create_user()
            system = data_setup.create_system(status=u'Automated',
                    shared=False, lab_controller=self.lab_controller)
            system.custom_access_policy.add_rule(
                permission=SystemPermission.reserve, user=user2)
            job1 = data_setup.create_job(owner=user1)
            job1.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires force="%s"/>'
                % system.fqdn)
            job2 = data_setup.create_job(owner=user2)
            job2.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires force="%s"/>'
                % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job1.id)
            self.assertEqual(job.status, TaskStatus.aborted)
            job = Job.query.get(job2.id)
            self.assertEqual(job.status, TaskStatus.processed)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1162451
    def test_recipes_with_force_are_queued(self):
        with session.begin():
            # Two recipes with force="" for the same system.
            system = data_setup.create_system(status=u'Manual', shared=True,
                    lab_controller=self.lab_controller)
            job1 = data_setup.create_job()
            job1.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires force="%s"/>' % system.fqdn)
            job2 = data_setup.create_job()
            job2.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires force="%s"/>' % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.abort_dead_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job1 = Job.query.get(job1.id)
            self.assertEqual(job1.status, TaskStatus.scheduled)
            job2 = Job.query.get(job2.id)
            self.assertEqual(job2.status, TaskStatus.queued)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1384527
    def test_force_ignores_excluded_families(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree()
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller,
                    exclude_osmajor=[distro_tree.distro.osversion.osmajor])
            self.assertFalse(system.compatible_with_distro_tree(
                arch=distro_tree.arch,
                osmajor=distro_tree.distro.osversion.osmajor.osmajor,
                osminor=distro_tree.distro.osversion.osminor))
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0].host_requires = \
                '<hostRequires force="%s"/>' % system.fqdn

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.scheduled)

    def test_recipe_state_reserved(self):
        with session.begin():
            recipe = data_setup.create_recipe(
                task_list=[Task.by_name(u'/distribution/check-install')] * 2,
                reservesys=True,
                reservesys_duration=3600,
            )
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(job.recipesets[0].recipes[0])
            job._mark_dirty()
            job_id = job.id

        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.by_id(job_id)
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.reserved)
            assert_datetime_within(job.recipesets[0].recipes[0].watchdog.kill_time,
                                   tolerance=datetime.timedelta(seconds=10),
                                   reference=datetime.datetime.utcnow() +  \
                                   datetime.timedelta(seconds=3600))

        # return the reservation
        with session.begin():
            job = Job.by_id(job_id)
            self.assertFalse(job.is_dirty)
            job.recipesets[0].recipes[0].return_reservation()
            self.assertTrue(job.is_dirty)

        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.by_id(job_id)
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.completed)
            self.assertEqual(job.status,
                             TaskStatus.completed)

    def test_recipe_is_not_reserved_when_no_systems_match(self):

        with session.begin():
            recipe = data_setup.create_recipe(
                task_list=[Task.by_name(u'/distribution/check-install')] * 2,
                reservesys=True)
            recipe._host_requires = (
                u'<hostRequires><hostname op="=" value="Ineverexisted.fqdn"/></hostRequires>')
            job = data_setup.create_job_for_recipes([recipe])

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.aborted)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1558828
    def test_not_enough_systems_logic(self):
        # LC1 has 1 system: A
        # LC2 has 2 systems: B, C
        # The recipe set has 2 recipes which can use any of A, B, or C.
        # B and C are currently reserved.
        # LC1 should be excluded, both recipes will remain queued waiting for B and C.
        with session.begin():
            lc1 = data_setup.create_labcontroller()
            lc2 = data_setup.create_labcontroller()
            system_a = data_setup.create_system(lab_controller=lc1)
            system_b = data_setup.create_system(lab_controller=lc2)
            system_c = data_setup.create_system(lab_controller=lc2)
            pool = data_setup.create_system_pool(systems=[system_a, system_b, system_c])
            job = data_setup.create_job(num_recipes=2)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><pool value="%s"/></hostRequires>' % pool.name)
            job.recipesets[0].recipes[1]._host_requires = (
                    '<hostRequires><pool value="%s"/></hostRequires>' % pool.name)
            data_setup.create_manual_reservation(system_b)
            data_setup.create_manual_reservation(system_c)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEquals(job.recipesets[0].recipes[0].status, TaskStatus.queued)
            self.assertEquals(job.recipesets[0].recipes[1].status, TaskStatus.queued)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1120052
    def test_bz1120052(self):
        # Due to the complexities of the not enough systems logic, the
        # triggering circumstances for this bug are quite intricate...
        # LC has 3 systems: A, B, C
        # RS has 4 recipes:
        #     R0 -> [A]
        #     R1 -> [B]
        #     R2 -> [A, B]
        #     R3 -> [A, B, C]
        # The recipe set is aborted because R2 will have no candidates (they
        # will be removed in favour of R0 and R1).
        with session.begin():
            lc = data_setup.create_labcontroller()
            system_a = data_setup.create_system(lab_controller=lc)
            system_b = data_setup.create_system(lab_controller=lc)
            system_c = data_setup.create_system(lab_controller=lc)
            job = data_setup.create_job(num_recipes=4)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname value="%s"/></hostRequires>'
                    % system_a.fqdn)
            job.recipesets[0].recipes[1]._host_requires = (
                    '<hostRequires><hostname value="%s"/></hostRequires>'
                    % system_b.fqdn)
            job.recipesets[0].recipes[2]._host_requires = (
                    '<hostRequires><or><hostname value="%s"/>'
                    '<hostname value="%s"/></or></hostRequires>'
                    % (system_a.fqdn, system_b.fqdn))
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEquals(job.recipesets[0].status, TaskStatus.aborted)
            expected_msg = ('Recipe ID %s does not match any systems'
                    % job.recipesets[0].recipes[2].id)
            for recipe in job.all_recipes:
                self.assertEquals(recipe.tasks[0].results[-1].log, expected_msg)

    def test_priority_is_bumped_when_recipe_matches_one_system(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.lab_controller)
            recipe = data_setup.create_recipe()
            recipe._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
            job = data_setup.create_job_for_recipes([recipe],
                    priority=TaskPriority.low)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)
            self.assertEqual(job.recipesets[0].priority, TaskPriority.medium)
            # https://bugzilla.redhat.com/show_bug.cgi?id=1369599
            self.assertEquals(len(job.recipesets[0].activity), 1)
            activity_entry = job.recipesets[0].activity[0]
            self.assertEquals(activity_entry.user, None)
            self.assertEquals(activity_entry.service, u'Scheduler')
            self.assertEquals(activity_entry.action, u'Changed')
            self.assertEquals(activity_entry.field_name, u'Priority')
            self.assertEquals(activity_entry.old_value, u'Low')
            self.assertEquals(activity_entry.new_value, u'Medium')

    def test_installation_table_parameters_filled_out_at_provisioning_time(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            distro_tree = data_setup.create_distro_tree(distro_name=u'MyUniqueLinux5-5',
                                                        lab_controllers=[lc])
            user = data_setup.create_user(user_name=u'test-job-owner',
                                          email_address=u'test-job-owner@example.com')
        jobxml = lxml.etree.fromstring('''
                    <job>
                        <whiteboard>
                            so pretty
                        </whiteboard>
                        <recipeSet>
                            <recipe>
                                <distroRequires>
                                    <distro_name op="=" value="MyUniqueLinux5-5" />
                                </distroRequires>
                                <hostRequires/>
                                <task name="/distribution/check-install"/>
                            </recipe>
                        </recipeSet>
                    </job>
                ''')
        controller = Jobs()
        with session.begin():
            job = controller.process_xmljob(jobxml, user)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        with session.begin():
            job = Job.query.get(job.id)
            recipe = job.recipesets[0].recipes[0]
        self.assertEqual(recipe.installation.tree_url,
                         u'nfs://%s:/distros/MyUniqueLinux5-5/Server/i386/os/' % lc)
        self.assertEqual(recipe.installation.kernel_path, u'pxeboot/vmlinuz')
        self.assertEqual(recipe.installation.initrd_path, u'pxeboot/initrd')

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_provision_does_not_fail_when_kickstart_element_used_with_custom_distro(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            user = data_setup.create_user(user_name=u'test-job-owner',
                                          email_address=u'test-job-owner@example.com')
        jobxml = lxml.etree.fromstring('''
                    <job>
                        <whiteboard>
                            so pretty
                        </whiteboard>
                        <recipeSet>
                            <recipe>
                            <kickstart> Awesome kickstart stuff </kickstart>
                                <distro>
                                    <tree url="ftp://dummylab.example.com/distros/PinkStockingLinux1.0/Server/i386/os/"/>
                                    <initrd url="pxeboot/initrd"/>
                                    <kernel url="pxeboot/vmlinuz"/>
                                    <arch value="i386"/>
                                    <osversion major="RedHatEnterpriseLinux7" minor="4"/>
                                    <name value="MyCustomLinux1.0"/>
                                    <variant value="Server"/>
                                </distro>
                                <hostRequires/>
                                <task name="/distribution/check-install"/>
                            </recipe>
                        </recipeSet>
                    </job>
                ''')
        controller = Jobs()
        with session.begin():
            job = controller.process_xmljob(jobxml, user)
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        with session.begin():
            job = Job.query.get(job.id)
            recipe = job.recipesets[0].recipes[0]
        self.assertIn('Awesome kickstart stuff', recipe.installation.rendered_kickstart.kickstart)

    def test_user_defined_recipe_provisioning_of_unknown_osmajor_does_not_fail(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            recipe = data_setup.create_recipe(custom_distro=True, osmajor='IDontExist1',
                                              task_list=[Task.by_name(u'/distribution/check-install')] * 2)
            job = data_setup.create_job_for_recipes([recipe])
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)

    def test_user_defined_distro_provisioning_uses_correct_exclusions_and_kernel_options(self):
        with session.begin():
            osmajor = OSMajor.by_name(u'DansAwesomeLinux6')
            lc = data_setup.create_labcontroller()
            # exclude the osmajor used on system 1, not on 2
            excluded_system = data_setup.create_system(lab_controller=lc, exclude_osmajor=[osmajor])
            included_system = data_setup.create_system(lab_controller=lc)
            arch = Arch.by_name('i386')
            included_system.provisions[arch] = Provision(arch=arch, kernel_options='anwesha')
            recipe = data_setup.create_recipe(custom_distro=True, osmajor='DansAwesomeLinux6', arch='i386',
                                              task_list=[Task.by_name(u'/distribution/check-install')] * 2)
            job = data_setup.create_job_for_recipes([recipe])
            job.recipesets[0].recipes[0]._host_requires = (u"""
                   <hostRequires>
                     <labcontroller op="=" value="%s"/>
                   </hostRequires>
                   """ % (lc.fqdn))
            session.flush()
            job_id = job.id
            excluded_system_id = excluded_system.id
            included_system_id = included_system.id

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            excluded_system = System.query.get(excluded_system_id)
            included_system = System.query.get(included_system_id)
            self.assertEqual(job.status, TaskStatus.processed)
            candidate_systems = job.recipesets[0].recipes[0].systems
            # assert that system without excluded osmajor is chosen
            self.assertEqual(len(candidate_systems), 1)
            self.assertNotEqual(candidate_systems[0], excluded_system)
            self.assertEqual(candidate_systems[0], included_system)

        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.scheduled)

        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.waiting)
            # assert correct kernel options are used
            self.assertIn('anwesha', job.recipesets[0].recipes[0].installation.kernel_options)

    def test_recipesets_provisioned_when_guest_recipe_is_user_defined(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            host_recipe = data_setup.create_recipe(arch='i386')
            guest_recipe = data_setup.create_guestrecipe(host=host_recipe, custom_distro=True,
                                                         osmajor='DansAwesomeLinux6', arch='i386',
                                                         task_list=[Task.by_name(u'/distribution/check-install')] * 2)
            job = data_setup.create_job_for_recipes([host_recipe, guest_recipe])
            session.flush()
            job_id = job.id

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.scheduled)

        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.waiting)


    def test_recipesets_provisioned_when_host_recipe_is_user_defined(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            host_recipe = data_setup.create_recipe(custom_distro=True, osmajor='DansAwesomeLinux6',
                                                   task_list=[Task.by_name(u'/distribution/check-install')] * 2)
            guest_recipe = data_setup.create_guestrecipe(host=host_recipe, custom_distro=True)
            job = data_setup.create_job_for_recipes([host_recipe, guest_recipe])
            session.flush()
            job_id = job.id
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.waiting)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1568224c12
    @patch.object(Recipe, 'reduced_install_options')
    def test_beakerd_aborts_recipe_when_provision_fails(self, recipe_mock):
        # provisioning the first recipe will succeed, but the second will blow up with an AttributeError
        recipe_mock.side_effect = [InstallOptions.from_strings('', '', ''),
                                   AttributeError("'NoneType' object has no attribute 'distro_name'")]

        with session.begin():
            lc = data_setup.create_labcontroller()
            data_setup.create_system(lab_controller=lc)
            data_setup.create_system(lab_controller=lc)
            job = data_setup.create_job(num_recipes=2)
            session.flush()
            job_id = job.id

        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.schedule_pending_systems()
        beakerd.update_dirty_jobs()
        beakerd.provision_scheduled_recipesets()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.query.get(job_id)
            self.assertFalse(job.is_dirty)
            self.assertEqual(1, len(job.recipesets))
            recipeset = job.recipesets[0]
            self.assertEqual(recipeset.status, TaskStatus.aborted)
            self.assertEqual(2, len(recipeset.recipes))
            r1, r2 = recipeset.recipes
            self.assertEqual(r1.status, TaskStatus.aborted)
            self.assertEqual(r2.status, TaskStatus.aborted)

            msg = u"Failed to provision recipeid %s, 'NoneType' object has no attribute 'distro_name'" % r2.id
            self.assertEqual(1, len(r1.tasks))
            self.assertEqual(msg, r1.tasks[0].results[0].log)
            self.assertEqual(1, len(r2.tasks))
            self.assertEqual(msg, r2.tasks[0].results[0].log)


class TestProvisionVirtRecipes(DatabaseTestCase):

    def setUp(self):
        if not config.get('openstack.identity_api_url'):
            raise SkipTest('OpenStack Integration is not enabled')
        with session.begin():
            self.user = data_setup.create_user()
            data_setup.create_keystone_trust(self.user)
            self.virt_manager = dynamic_virt.VirtManager(self.user)
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe], owner=self.user)
            # We want our test recipe to go to OpenStack, so make sure there
            # are no shared idle systems left behind by previous tests. If
            # there are, the scheduler will prefer to use those instead of
            # OpenStack.
            System.query.filter(System.status == SystemStatus.automated)\
                    .update(dict(status=SystemStatus.removed), synchronize_session=False)

    def tearDown(self):
        with session.begin():
            recipe = Recipe.query.get(self.recipe.id)
            if recipe.resource and not recipe.resource.instance_deleted:
                self.virt_manager.destroy_vm(recipe.resource)

    def _run_beakerd_once(self):
        beakerd.process_new_recipes()
        beakerd.update_dirty_jobs()
        beakerd.queue_processed_recipesets()
        beakerd.update_dirty_jobs()
        beakerd.provision_virt_recipes()
        beakerd.update_dirty_jobs()

    def test_openstack_instance_created(self):
        self._run_beakerd_once()
        with session.begin():
            recipe = Recipe.query.get(self.recipe.id)
            self.assertIsNotNone(recipe,
                                 "Failed to get recipe ID %s" % self.recipe.id)
            self.assertIsNotNone(recipe.resource,
                                 "Recipe ID %s does not have a resource" % self.recipe.id)
            self.assertEquals(recipe.status, TaskStatus.installing)
            self.assertIsNotNone(
                recipe.resource.instance_created,
                "Recipe ID %s resource does not have instance_created" % self.recipe.id)
            instance = self.virt_manager.novaclient.servers.get(
                recipe.resource.instance_id)
            self.assertIsNotNone(
                instance,
                "Instance not found for recipe ID %s, resource instance ID %s"
                % (self.recipe.id, recipe.resource.instance_id))
            self.assertTrue(instance.status, u'ACTIVE')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1361936
    def test_after_reboot_watchdog_killtime_extended_on_virt_recipes(self):
        self._run_beakerd_once()
        with session.begin():
            recipe = Recipe.query.get(self.recipe.id)
            self.assertEquals(recipe.status, TaskStatus.installing)
            self.assertIsNotNone(recipe.installation.rebooted)
            self.assertIsNotNone(recipe.watchdog.kill_time)
            assert_datetime_within(
                recipe.watchdog.kill_time,
                tolerance=datetime.timedelta(seconds=10),
                reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=3000))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1397649
    def test_cheapest_OpenStack_flavor_should_be_picked(self):
        self._run_beakerd_once()
        with session.begin():
            recipe = Recipe.query.get(self.recipe.id)
            self.assertIsNotNone(recipe,
                                 "Failed to get recipe ID %s" % self.recipe.id)
            self.assertIsNotNone(recipe.resource,
                                 "Recipe ID %s does not have a resource" % self.recipe.id)
            instance = self.virt_manager.novaclient.servers.get(recipe.resource.instance_id)
            available_flavors = self.virt_manager.available_flavors()
            # remove the flavor that has no disk
            # and flavor with really small disk
            for flavor in available_flavors:
                if flavor.disk < 10:
                    available_flavors.remove(flavor)
            # cheapest flavor has the smallest disk and ram
            # id guarantees consistency of our results
            cheapest_flavor = min(available_flavors, key=lambda flavor: (flavor.ram, flavor.disk, flavor.id))
            instance_flavor = self.virt_manager.novaclient.flavors.get(instance.flavor['id'])
            self.assertEquals(instance_flavor.ram, cheapest_flavor.ram)
            self.assertEquals(instance_flavor.id, cheapest_flavor.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1396851
    def test_floating_ip_is_assigned(self):
        if not self.virt_manager.is_create_floating_ip:
            raise SkipTest('create_floating_ip is False')
        self._run_beakerd_once()
        with session.begin():
            recipe = Recipe.query.get(self.recipe.id)
            self.assertIsNotNone(recipe,
                                 "Failed to get recipe ID %s" % self.recipe.id)
            self.assertIsNotNone(recipe.resource,
                                 "Recipe ID %s does not have a resource" % self.recipe.id)
            resource_instance_id = str(recipe.resource.instance_id)
            port = self.virt_manager._get_instance_port(resource_instance_id)
            fips = self.virt_manager.neutronclient.list_floatingips(port_id=port['id'])
            # the port of the instance should be associated with a floating ip
            self.assertEquals(len(fips['floatingips']), 1)
            self.assertEquals(fips['floatingips'][0]['floating_ip_address'],
                              str(recipe.resource.floating_ip))

    def test_cleanup_openstack(self):
        self._run_beakerd_once()
        with session.begin():
            recipe = Recipe.query.get(self.recipe.id)
            self.assertIsNotNone(recipe,
                                 "Failed to get recipe ID %s" % self.recipe.id)
            self.assertIsNotNone(recipe.resource,
                                 "Recipe ID %s does not have a resource" % self.recipe.id)
            instance = self.virt_manager.novaclient.servers.get(
                recipe.resource.instance_id)
            self.assertTrue(instance.status, u'ACTIVE')
            recipe.recipeset.job.cancel()
            recipe.recipeset.job.update_status()
        # the instance should be deleted
        try:
            self.virt_manager.novaclient.servers.get(recipe.resource.instance_id)
            self.fail('should raise')
        except Exception, e:
            self.assertIn('Instance %s could not be found' % recipe.resource.instance_id,
                    e.message)
        if self.virt_manager.is_create_floating_ip:
            # the network should be deleted
            try:
                self.virt_manager.neutronclient.show_network(recipe.resource.network_id)
                self.fail('should raise')
            except Exception, e:
                # neutronclient on RHEL7+ raise NetworkNotFoundClient for missing nets
                if hasattr(e, 'status_code'):
                    self.assertEquals(e.status_code, 404)
                else:
                    self.assertEquals(e.response.status_code, 404)
            # the subnet should be deleted
            try:
                self.virt_manager.neutronclient.show_subnet(recipe.resource.subnet_id)
                self.fail('should raise')
            except Exception, e:
                if hasattr(e, 'status_code'):
                    self.assertEquals(e.status_code, 404)
                else:
                    self.assertEquals(e.response.status_code, 404)
            # the router should be deleted
            try:
                self.virt_manager.neutronclient.show_router(recipe.resource.router_id)
                self.fail('should raise')
            except Exception, e:
                if hasattr(e, 'status_code'):
                    self.assertEquals(e.status_code, 404)
                else:
                    self.assertEquals(e.response.status_code, 404)
            # the floating IP address should be deleted
            self.assertFalse(self.virt_manager.neutronclient.list_floatingips(
                floating_ip_address=recipe.resource.floating_ip)['floatingips'])

@patch('bkr.server.tools.beakerd.metrics')
class TestBeakerdMetrics(DatabaseTestCase):

    def setUp(self):
        session.begin()
        try:
            # Other tests might have left behind systems and system commands
            # and running recipes, so we remove or cancel them all so they
            # don't pollute our metrics
            manually_reserved = System.query.filter(System.open_reservation != None)
            for system in manually_reserved:
                data_setup.unreserve_manual(system)
            systems = System.query.filter(System.status != SystemStatus.removed)
            for system in systems:
                system.status = SystemStatus.removed

            session.flush()
            commands = Command.query.filter(not_(Command.finished))
            for command in commands:
                command.change_status(CommandStatus.aborted)
            running = Recipe.query.filter(not_(Recipe.status.in_(
                [s for s in TaskStatus if s.finished])))
            for recipe in running:
                recipe.recipeset.cancel()
                recipe.recipeset.job.update_status()
        except Exception, e:
            session.rollback()
            raise

    def tearDown(self):
        session.rollback()

    def test_system_count_metrics(self, mock_metrics):
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
        for name, value in expected.iteritems():
            mock_metrics.measure.assert_any_call(name, value)

    def test_system_count_metrics_uses_active_access_policy(self, mock_metrics):
        lc = data_setup.create_labcontroller()
        # not shared
        data_setup.create_system(lab_controller=lc, shared=False)
        # shared via custom access policy
        data_setup.create_system(lab_controller=lc, shared=True)
        # shared via pool policy
        shared_via_pool = data_setup.create_system(lab_controller=lc, shared=True)
        pool = data_setup.create_system_pool(systems=[shared_via_pool])
        pool.access_policy.add_rule(SystemPermission.reserve, everybody=True)
        shared_via_pool.active_access_policy = pool.access_policy
        # restricted via pool policy
        restricted_via_pool = data_setup.create_system(lab_controller=lc, shared=True)
        restrictive_pool = data_setup.create_system_pool(systems=[shared_via_pool])
        restricted_via_pool.active_access_policy = restrictive_pool.access_policy
        session.flush()
        beakerd.system_count_metrics()
        mock_metrics.measure.assert_any_call(
                'gauges.systems_idle_automated.shared', 2)

    def test_recipe_count_metrics(self, mock_metrics):
        gauges = [
            'gauges.recipes_scheduled',
            'gauges.recipes_running',
            'gauges.recipes_waiting',
            'gauges.recipes_processed',
            'gauges.recipes_new',
            'gauges.recipes_queued',
            'gauges.recipes_reserved',
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
        lc = data_setup.create_labcontroller()
        recipes = []
        for arch in u"i386 x86_64 ppc ppc64".split():
            data_setup.create_system(arch=arch, lab_controller=lc, shared=True)
            dt = data_setup.create_distro_tree(arch=arch)
            recipe = data_setup.create_recipe(distro_tree=dt)
            user = data_setup.create_user()
            user.openstack_trust_id = u'dummpy_openstack_trust_id_%s' % user
            data_setup.create_job_for_recipes([recipe], owner=user)
            recipes.append(recipe)
            expected['gauges.recipes_new.all'] += 1
            expected['gauges.recipes_new.dynamic_virt_possible'] += 1
            expected['gauges.recipes_new.by_arch.%s' % arch] += 1
        session.flush()
        beakerd.recipe_count_metrics()
        for name, value in expected.iteritems():
            mock_metrics.measure.assert_any_call(name, value)
        # Processing the recipes should set their virt status correctly
        mock_metrics.reset_mock()
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
            recipe.recipeset.job.update_status()
        session.flush()
        beakerd.recipe_count_metrics()
        for name, value in expected.iteritems():
            mock_metrics.measure.assert_any_call(name, value)

    def test_dirty_job_metrics(self, mock_metrics):
        # Ensure that any dirty jobs left behind by
        # an unrelated test are marked clean to avoid
        # contaminating the metrics test
        for dirty in Job.query.filter(Job.is_dirty):
            dirty._mark_clean()

        job = data_setup.create_running_job()
        self.assertFalse(job.is_dirty)
        session.flush()
        beakerd.dirty_job_metrics()
        mock_metrics.measure.assert_called_with('gauges.dirty_jobs', 0)

        mock_metrics.reset_mock()
        job.cancel()
        self.assertTrue(job.is_dirty)
        session.flush()
        beakerd.dirty_job_metrics()
        mock_metrics.measure.assert_called_with('gauges.dirty_jobs', 1)

        mock_metrics.reset_mock()
        job.update_status()
        self.assertFalse(job.is_dirty)
        session.flush()
        beakerd.dirty_job_metrics()
        mock_metrics.measure.assert_called_with('gauges.dirty_jobs', 0)

    def test_system_command_metrics(self, mock_metrics):
        lc = data_setup.create_labcontroller(fqdn=u'testcommandmetrics.invalid')
        system = data_setup.create_system(lab_controller=lc, arch=u'x86_64')
        data_setup.configure_system_power(system, power_type=u'drac')
        command = system.enqueue_command(u'on', service=u'testdata')

        categories = ['all', 'by_lab.testcommandmetrics_invalid',
                'by_arch.x86_64', 'by_power_type.drac']

        session.flush()
        beakerd.system_command_metrics()
        log.debug('Metrics calls were: %s', mock_metrics.measure.call_args_list)
        for category in categories:
            mock_metrics.measure.assert_any_call(
                    'gauges.system_commands_queued.%s' % category, 1)
            mock_metrics.measure.assert_any_call(
                    'gauges.system_commands_running.%s' % category, 0)

        mock_metrics.reset_mock()
        command.change_status(CommandStatus.running)
        session.flush()
        beakerd.system_command_metrics()
        log.debug('Metrics calls were: %s', mock_metrics.measure.call_args_list)
        for category in categories:
            mock_metrics.measure.assert_any_call(
                    'gauges.system_commands_queued.%s' % category, 0)
            mock_metrics.measure.assert_any_call(
                    'gauges.system_commands_running.%s' % category, 1)

        mock_metrics.reset_mock()
        command.change_status(CommandStatus.completed)
        session.flush()
        beakerd.system_command_metrics()
        log.debug('Metrics calls were: %s', mock_metrics.measure.call_args_list)
        for category in ['all']:
            mock_metrics.measure.assert_any_call(
                    'gauges.system_commands_queued.%s' % category, 0)
            mock_metrics.measure.assert_any_call(
                    'gauges.system_commands_running.%s' % category, 0)
