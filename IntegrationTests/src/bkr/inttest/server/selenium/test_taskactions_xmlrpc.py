
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest.server.selenium import XmlRpcTestCase
from bkr.inttest import data_setup

class TaskactionsTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
        self.server = self.get_server()
        self.server.auth.login_password(self.user.user_name, 'password')

    def test_running_status(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user)
            data_setup.mark_job_running(job)
        self.assertEquals(self.server.taskactions.task_info(job.t_id)['state'],
                'Running')
        self.assertEquals(self.server.taskactions.task_info(
                job.recipesets[0].t_id)['state'],
                'Running')
        self.assertEquals(self.server.taskactions.task_info(
                job.recipesets[0].recipes[0].t_id)['state'],
                'Running')
        self.assertEquals(self.server.taskactions.task_info(
                job.recipesets[0].recipes[0].tasks[0].t_id)['state'],
                'Running')

    def test_worker_info(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user)
            data_setup.mark_job_running(job)
            recipe = job.recipesets[0].recipes[0]
            system = recipe.resource.system
        self.assertEquals(self.server.taskactions.task_info(
                recipe.t_id)['worker'],
                {'name': system.fqdn})
        self.assertEquals(self.server.taskactions.task_info(
                recipe.tasks[0].t_id)['worker'],
                {'name': system.fqdn})

    # https://bugzilla.redhat.com/show_bug.cgi?id=1032653
    def test_worker_info_for_recipe_without_resource(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user)
            job.cancel()
            recipe = job.recipesets[0].recipes[0]
            self.assertEquals(recipe.resource, None)
        self.assertEquals(self.server.taskactions.task_info(
                recipe.t_id)['worker'], None)
        self.assertEquals(self.server.taskactions.task_info(
                recipe.tasks[0].t_id)['worker'], None)
