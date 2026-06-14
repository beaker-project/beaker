
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Regression tests for missing authorization checks on the XML-RPC
jobs.stop(), recipesets.stop(), recipes.stop(), and recipetasks.stop()
endpoints.
"""

import xmlrpclib
from bkr.server.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import TaskStatus


class UnauthorizedJobCancelViaJobsStopTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.victim = data_setup.create_user(password=u'victim')
            self.attacker = data_setup.create_user(password=u'attacker')
            self.job = data_setup.create_running_job(owner=self.victim)
            self.job_id = self.job.id
        self.server = self.get_server()
        self.server.auth.login_password(self.attacker.user_name, 'attacker')

    def test_taskactions_stop_rejects_unauthorized_user(self):
        """Baseline: the protected path correctly denies the attacker."""
        try:
            self.server.taskactions.stop(
                'J:%s' % self.job_id, 'cancel', 'authz test')
            self.fail('taskactions.stop should have denied the attacker')
        except xmlrpclib.Fault, e:
            self.assertIn("don't have permission", e.faultString)

    def test_jobs_stop_rejects_unauthorized_user(self):
        try:
            self.server.jobs.stop(self.job_id, 'cancel', 'authz test')
            self.fail('jobs.stop should have denied the attacker')
        except xmlrpclib.Fault, e:
            self.assertIn("don't have permission", e.faultString)
        with session.begin():
            session.refresh(self.job)
            self.assertNotEqual(self.job.status, TaskStatus.cancelled,
                'Job was cancelled despite the attacker not owning it')


class UnauthorizedCancelViaRecipeSetsStopTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.victim = data_setup.create_user(password=u'victim')
            self.attacker = data_setup.create_user(password=u'attacker')
            self.job = data_setup.create_running_job(owner=self.victim)
            self.recipeset_id = self.job.recipesets[0].id
        self.server = self.get_server()
        self.server.auth.login_password(self.attacker.user_name, 'attacker')

    def test_recipesets_stop_rejects_unauthorized_user(self):
        try:
            self.server.recipesets.stop(
                self.recipeset_id, 'cancel', 'authz test')
            self.fail('recipesets.stop should have denied the attacker')
        except xmlrpclib.Fault, e:
            self.assertIn("don't have permission", e.faultString)


class UnauthorizedCancelViaRecipesStopTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.victim = data_setup.create_user(password=u'victim')
            self.attacker = data_setup.create_user(password=u'attacker')
            self.job = data_setup.create_running_job(owner=self.victim)
            self.recipe_id = self.job.recipesets[0].recipes[0].id
        self.server = self.get_server()
        self.server.auth.login_password(self.attacker.user_name, 'attacker')

    def test_recipes_stop_rejects_unauthorized_user(self):
        try:
            self.server.recipes.stop(
                self.recipe_id, 'cancel', 'authz test')
            self.fail('recipes.stop should have denied the attacker')
        except xmlrpclib.Fault, e:
            self.assertIn("don't have permission", e.faultString)


class UnauthorizedCancelViaRecipeTasksStopTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.victim = data_setup.create_user(password=u'victim')
            self.attacker = data_setup.create_user(password=u'attacker')
            self.job = data_setup.create_running_job(owner=self.victim)
            self.task_id = self.job.recipesets[0].recipes[0].tasks[0].id
        self.server = self.get_server()
        self.server.auth.login_password(self.attacker.user_name, 'attacker')

    def test_recipetasks_stop_rejects_unauthorized_user(self):
        try:
            self.server.recipetasks.stop(
                self.task_id, 'cancel', 'authz test')
            self.fail('recipetasks.stop should have denied the attacker')
        except xmlrpclib.Fault, e:
            self.assertIn("don't have permission", e.faultString)
