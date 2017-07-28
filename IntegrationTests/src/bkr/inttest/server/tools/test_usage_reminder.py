
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime, timedelta
from turbogears.database import session
from bkr.common import __version__
from bkr.inttest import data_setup, DatabaseTestCase
from bkr.server.tools.usage_reminder import BeakerUsage
from bkr.server.util import absolute_url
from bkr.inttest.server.tools import run_command

class TestUsageReminder(DatabaseTestCase):
    def setUp(self):
        self.user = data_setup.create_user()
        self.reservation_expiry = 24
        self.reservation_length = 3
        self.waiting_recipe_age = 1
        self.delayed_job_age = 14

    def test_version(self):
        out = run_command('usage_reminder.py', 'beaker-usage-reminder', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_expiring_reservation(self):
        with session.begin():
            # recipe running /distribution/reservesys expiring soon
            expiring_soon = data_setup.create_recipe_reservation(self.user, u'/distribution/reservesys',
                                                          (self.reservation_expiry - 1) * 3600)
            # recipe running /distribution/reservesys expiring after the cut-off
            expiring_later = data_setup.create_recipe_reservation(self.user, u'/distribution/reservesys',
                                                          (self.reservation_expiry * 2) * 3600)
            # recipe expiring soon but running a real task
            not_reserved = data_setup.create_recipe_reservation(self.user, u'/something/else',
                                                         (self.reservation_expiry - 1) * 3600)
        beaker_usage = BeakerUsage(self.user, self.reservation_expiry, self.reservation_length,
                                   self.waiting_recipe_age, self.delayed_job_age)
        expiring_reservations = beaker_usage.expiring_reservations()
        self.assertEqual(len(expiring_reservations), 1)
        self.assertEqual(expiring_reservations[0][1], expiring_soon.resource.fqdn)

    def test_open_in_demand_systems(self):
        with session.begin():
            # system with waiting recipes
            system_with_waiting_recipes = data_setup.create_system()
            data_setup.create_manual_reservation(system_with_waiting_recipes,
                                                 start=datetime.utcnow() - timedelta(days=self.reservation_length),
                                                 user=self.user)
            recipe = data_setup.create_recipe()
            recipe.systems[:] = [system_with_waiting_recipes]
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_job_queued(job)
            job.recipesets[0].queue_time = datetime.utcnow() - timedelta(hours=self.waiting_recipe_age)
            # system with no waiting recipes
            system_without_waiting_recipes = data_setup.create_system()
            data_setup.create_manual_reservation(system_without_waiting_recipes,
                                                 start=datetime.utcnow() - timedelta(days=self.reservation_length),
                                                 user=self.user)
        beaker_usage = BeakerUsage(self.user, self.reservation_expiry, self.reservation_length,
                               self.waiting_recipe_age, self.delayed_job_age)
        open_in_demand_systems = beaker_usage.open_in_demand_systems()
        self.assertEqual(len(open_in_demand_systems), 1)
        self.assertEqual(open_in_demand_systems[0][1], 1)
        self.assertEqual(open_in_demand_systems[0][2], system_with_waiting_recipes.fqdn)

    def test_delayed_jobs(self):
        with session.begin():
            # Create a queued job that was submitted a long time ago
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            job.owner = self.user
            data_setup.mark_job_queued(job)
            job.recipesets[0].queue_time = datetime.utcnow() - timedelta(days=self.delayed_job_age)
            # create a job with two recipes, one Queued and one Scheduled
            # which was submitted a long time ago
            queued_recipe = data_setup.create_recipe()
            scheduled_recipe = data_setup.create_recipe()
            job_with_multiple_recipes = data_setup.create_job_for_recipes([queued_recipe, scheduled_recipe])
            job_with_multiple_recipes.owner = self.user
            # mark recipe Queued
            queued_recipe.process()
            queued_recipe.queue()
            # mark recipe Scheduled
            scheduled_recipe.process()
            scheduled_recipe.queue()
            scheduled_recipe.schedule()
            data_setup.mark_job_queued(job_with_multiple_recipes)
            job_with_multiple_recipes.recipesets[0].queue_time = datetime.utcnow()\
                - timedelta(days=self.delayed_job_age)
            # create a new submmited job for just now
            recently_submmited_job = data_setup.create_job_for_recipes([recipe])
            recently_submmited_job.owner = self.user
            data_setup.mark_job_queued(recently_submmited_job)
        beaker_usage = BeakerUsage(self.user, self.reservation_expiry, self.reservation_length,
                               self.waiting_recipe_age, self.delayed_job_age)
        delayed_jobs = beaker_usage.delayed_jobs()
        self.assertEqual(len(delayed_jobs), 2)
        self.assertEqual(absolute_url('/jobs/%s' % job.id), delayed_jobs[0][1])
        self.assertEqual(absolute_url('/jobs/%s' % job_with_multiple_recipes.id), delayed_jobs[1][1])
