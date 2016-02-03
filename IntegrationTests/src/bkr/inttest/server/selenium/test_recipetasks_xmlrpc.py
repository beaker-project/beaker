
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from turbogears.database import session
from bkr.server.model import TaskStatus, TaskResult
from bkr.inttest import data_setup
from bkr.inttest.assertions import assert_datetime_within
from bkr.inttest.server.selenium import XmlRpcTestCase

class RecipeTasksXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
        self.server = self.get_server()

    def test_peer_roles(self):
        with session.begin():
            dt = data_setup.create_distro_tree()
            lc = data_setup.create_labcontroller()
            systems = [
                data_setup.create_system(fqdn=u'server.peer-roles.invalid', lab_controller=lc),
                data_setup.create_system(fqdn=u'clientone.peer-roles.invalid', lab_controller=lc),
                data_setup.create_system(fqdn=u'clienttwo.peer-roles.invalid', lab_controller=lc),
            ]
            job = data_setup.create_job_for_recipes([
                data_setup.create_recipe(distro_tree=dt, role=u'SERVERS'),
                data_setup.create_recipe(distro_tree=dt, role=u'CLIENTS'),
                data_setup.create_recipe(distro_tree=dt, role=u'CLIENTS'),
            ])
            job.recipesets[0].recipes[0].tasks[0].role = None
            # Normally you wouldn't use the same role name with different 
            # meaning at the task level, because that would just get 
            # confusing... but it is possible
            job.recipesets[0].recipes[1].tasks[0].role = u'SERVERS'
            job.recipesets[0].recipes[2].tasks[0].role = u'CLIENTTWO'
            for i in range(3):
                data_setup.mark_recipe_running(job.recipesets[0].recipes[i], system=systems[i])
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        expected = {
            'SERVERS': ['server.peer-roles.invalid', 'clientone.peer-roles.invalid'],
            'CLIENTS': ['clientone.peer-roles.invalid', 'clienttwo.peer-roles.invalid'],
            'None': ['server.peer-roles.invalid'],
            'CLIENTTWO': ['clienttwo.peer-roles.invalid'],
        }
        for i in range(3):
            self.assertEquals(self.server.recipes.tasks.peer_roles(
                    job.recipesets[0].recipes[i].tasks[0].id),
                    expected)

    # https://bugzilla.redhat.com/show_bug.cgi?id=951283
    def test_role_fqdns_not_duplicated(self):
        with session.begin():
            dt = data_setup.create_distro_tree()
            lc = data_setup.create_labcontroller()
            systems = [
                data_setup.create_system(fqdn=u'server.bz951283', lab_controller=lc),
                data_setup.create_system(fqdn=u'client.bz951283', lab_controller=lc),
            ]
            job = data_setup.create_job_for_recipes([
                data_setup.create_recipe(distro_tree=dt, role=u'SERVERS'),
                data_setup.create_recipe(distro_tree=dt, role=u'CLIENTS'),
            ])
            # same roles on the tasks as on the recipes
            job.recipesets[0].recipes[0].tasks[0].role = u'SERVERS'
            job.recipesets[0].recipes[1].tasks[0].role = u'CLIENTS'
            for i in range(2):
                data_setup.mark_recipe_running(job.recipesets[0].recipes[i], system=systems[i])
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        expected = {
            'SERVERS': ['server.bz951283'],
            'CLIENTS': ['client.bz951283'],
        }
        for i in range(2):
            self.assertEquals(self.server.recipes.tasks.peer_roles(
                    job.recipesets[0].recipes[i].tasks[0].id),
                    expected)

    # https://bugzilla.redhat.com/show_bug.cgi?id=952948
    def test_unknown_fqdns_dont_appear(self):
        # If we have a recipe where the FQDN is not known (for example 
        # a guest that hasn't finished installing yet), previously it would 
        # appear as the string 'None'. Now it's just not included.
        with session.begin():
            hostrecipe = data_setup.create_recipe(role=u'SERVERS')
            guestrecipe = data_setup.create_guestrecipe(host=hostrecipe,
                    role=u'CLIENTS')
            data_setup.create_job_for_recipes([hostrecipe, guestrecipe])
            system = data_setup.create_system(fqdn=u'host.bz952948',
                    lab_controller=self.lc)
            data_setup.mark_recipe_running(hostrecipe, system=system)
            data_setup.mark_recipe_waiting(guestrecipe)
            self.assertEquals(guestrecipe.resource.fqdn, None)
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.assertEquals(self.server.recipes.tasks.peer_roles(
                hostrecipe.tasks[0].id),
                {'SERVERS': ['host.bz952948'],
                 'STANDALONE': ['host.bz952948'],
                 'CLIENTS': []})
        self.assertEquals(self.server.recipes.tasks.peer_roles(
                guestrecipe.tasks[0].id),
                {'SERVERS': ['host.bz952948'],
                 'STANDALONE': ['host.bz952948'],
                 'CLIENTS': []})

    # https://bugzilla.redhat.com/show_bug.cgi?id=960434
    def test_task_roles_visible_between_hosts_and_guests(self):
        # Hosts and guests can all see each others' task roles now. Previously 
        # they were not visible to each other.
        with session.begin():
            hostrecipe = data_setup.create_recipe()
            guestrecipe_server = data_setup.create_guestrecipe(host=hostrecipe)
            guestrecipe_client = data_setup.create_guestrecipe(host=hostrecipe)
            job = data_setup.create_job_for_recipes([hostrecipe,
                    guestrecipe_server, guestrecipe_client])
            hostrecipe.tasks[0].role = u'SERVERS'
            guestrecipe_server.tasks[0].role = u'SERVERS'
            guestrecipe_client.tasks[0].role = u'CLIENTS'
            system = data_setup.create_system(fqdn=u'host.bz960434',
                    lab_controller=self.lc)
            data_setup.mark_recipe_running(hostrecipe, system=system)
            data_setup.mark_recipe_running(guestrecipe_server, fqdn=u'guestserver.bz960434')
            data_setup.mark_recipe_running(guestrecipe_client, fqdn=u'guestclient.bz960434')
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        expected_peer_roles = {
            'SERVERS': ['host.bz960434', 'guestserver.bz960434'],
            'CLIENTS': ['guestclient.bz960434'],
            'STANDALONE': ['host.bz960434', 'guestserver.bz960434', 'guestclient.bz960434'],
        }
        for recipe in [hostrecipe, guestrecipe_server, guestrecipe_client]:
            self.assertEquals(
                    self.server.recipes.tasks.peer_roles(recipe.tasks[0].id),
                    expected_peer_roles)
