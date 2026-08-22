# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
import lxml.etree
from six import assertRegex, text_type
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as requests_login, patch_json
from bkr.server.database import session
from bkr.server.model import LogRecipeTask, RecipeReservationCondition


class RecipeHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipes.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.recipe = data_setup.create_recipe()
            self.recipe_with_reservation_request = data_setup.create_recipe(reservesys=True)
            self.recipe_without_reservation_request = data_setup.create_recipe()
            self.job = data_setup.create_job_for_recipes([
                    self.recipe,
                    self.recipe_with_reservation_request,
                    self.recipe_without_reservation_request],
                    owner=self.owner)

    def test_get_recipe(self):
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['t_id'], self.recipe.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1361002
    def test_get_virt_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe, virt=True)
        response = requests.get(get_server_base() +
                'recipes/%s' % recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['resource']['instance_id'],
                text_type(recipe.resource.instance_id))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1324305
    def test_get_scheduled_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe)
            self.assertIsNone(recipe.watchdog.kill_time)
        response = requests.get(get_server_base() +
                'recipes/%s' % recipe.id,
                headers={'Accept': 'application/json'})
        json = response.json()
        self.assertEqual(json['t_id'], recipe.t_id)
        # time_remaining_seconds should be None as the recipe sits in Scheduled
        # with no watchdog kill time.
        self.assertIsNone(json['time_remaining_seconds'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1324401
    def test_set_vary_header(self):
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertIn('Vary', response.headers)

    def test_get_recipe_xml(self):
        response = requests.get(get_server_base() + 'recipes/%s.xml' % self.recipe.id)
        response.raise_for_status()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
                lxml.etree.tostring(self.recipe.to_xml(), pretty_print=True, encoding='utf8'),
                response.content)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319#c6
    def test_get_recipe_xml_without_logs(self):
        response = requests.get(get_server_base() + 'recipes/%s.xml?include_logs=false' % self.recipe.id)
        response.raise_for_status()
        self.assertNotIn('<log', response.text)

    def test_get_junit_xml(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        response = requests.get(get_server_base() + 'recipes/%s.junit.xml' % self.recipe.id)
        response.raise_for_status()
        self.assertEqual(response.status_code, 200)
        junitxml = lxml.etree.fromstring(response.content)
        self.assertEqual(junitxml.tag, 'testsuites')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1169838
    def test_trailing_slash_should_return_404(self):
        response = requests.get(get_server_base() + 'recipes/%s/' % self.recipe.id)
        self.assertEqual(response.status_code, 404)

    def test_get_recipe_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
        response = requests.get(get_server_base() +
                'recipes/%s/logs/recipe_path/dummy.txt' % recipe.id,
                allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/beaker/recipe_path/dummy.txt')

    def test_404_for_nonexistent_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
        response = requests.get(get_server_base() +
                'recipes/%s/logs/doesnotexist.log' % recipe.id,
                allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        assertRegex(self, response.text, 'Recipe log .* not found')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1622805
    def test_redirects_beah_log_to_restraint(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
            rt = recipe.tasks[0]
            rt.logs = [LogRecipeTask(server=u'http://dummy-archive-server/',
                                     filename=u'taskout.log')]
        # Client is looking for TESTOUT.log (old filename from Beah)
        # but the task only has taskout.log (new filename from Restraint)
        # so we expect to be redirected to that.
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/logs/TESTOUT.log' % (recipe.id, rt.id),
                allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/taskout.log')

    def test_anonymous_cannot_update_recipe(self):
        response = patch_json(get_server_base() +
                'recipes/%s' % self.recipe.id,
                data={'whiteboard': u'testwhiteboard'})
        self.assertEqual(response.status_code, 401)

    def test_can_update_recipe_whiteboard(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s' % self.recipe.id,
                session=s, data={'whiteboard': u'newwhiteboard'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.whiteboard, 'newwhiteboard')
            self.assertEqual(self.recipe.activity[0].field_name, u'Whiteboard')
            self.assertEqual(self.recipe.activity[0].action, u'Changed')
            self.assertEqual(self.recipe.activity[0].new_value, u'newwhiteboard')

    def test_anonymous_cannot_update_reservation_request(self):
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                data={'reserve': True, 'duration': 300})
        self.assertEqual(response.status_code, 401)

    def test_cannot_update_reservation_request_on_completed_recipe(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': False})
        self.assertEqual(response.status_code, 403)

    def test_cannot_update_reservation_request_if_duration_too_long(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 605000})
        self.assertEqual(response.status_code, 400)

    def test_can_update_reservation_request_to_reserve_system(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        # On a recipe with reservation request
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 300, 'when': 'onfail'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe_with_reservation_request.reservation_request.when,
                    RecipeReservationCondition.onfail)
            self.assertEqual(self.recipe_with_reservation_request.activity[0].field_name,
                    u'Reservation Condition')
            self.assertEqual(self.recipe_with_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEqual(self.recipe_with_reservation_request.activity[0].new_value,
                    u'onfail')
            self.assertEqual(self.recipe_with_reservation_request.reservation_request.duration,
                    300)
            self.assertEqual(self.recipe_with_reservation_request.activity[1].field_name,
                    u'Reservation Request')
            self.assertEqual(self.recipe_with_reservation_request.activity[1].action,
                    u'Changed')
            self.assertEqual(self.recipe_with_reservation_request.activity[1].new_value,
                    u'300')
        # On a recipe without reservation request
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_without_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 300, 'when': 'onfail'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.recipe_without_reservation_request.reservation_request)
            self.assertEqual(self.recipe_without_reservation_request.reservation_request.when,
                    RecipeReservationCondition.onfail)
            self.assertEqual(self.recipe_without_reservation_request.activity[0].field_name,
                    u'Reservation Condition')
            self.assertEqual(self.recipe_without_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEqual(self.recipe_without_reservation_request.activity[0].new_value,
                    u'onfail')
            self.assertEqual(self.recipe_without_reservation_request.reservation_request.duration,
                    300)
            self.assertEqual(self.recipe_without_reservation_request.activity[1].field_name,
                    u'Reservation Request')
            self.assertEqual(self.recipe_without_reservation_request.activity[1].action,
                    u'Changed')
            self.assertEqual(self.recipe_without_reservation_request.activity[1].new_value,
                    u'300')

    def test_can_update_reservation_request_to_not_reserve_the_system(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': False})
        response.raise_for_status()

        with session.begin():
            session.expire_all()
            self.assertFalse(self.recipe_with_reservation_request.reservation_request)
            self.assertEqual(self.recipe_with_reservation_request.activity[0].field_name,
                    u'Reservation Request')
            self.assertEqual(self.recipe_with_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEqual(self.recipe_with_reservation_request.activity[0].new_value,
                    None)

    def test_rejects_unrecognised_reserve_conditions(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'when': 'slartibartfast'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Invalid value for RecipeReservationCondition: '
                '%s is not one of onabort, onfail, onwarn, always'
                % repr(u'slartibartfast'))

    def test_anonymous_has_no_reviewed_state(self):
        # Reviewed state is per-user so anonymous should get "reviewed": null 
        # (neither true nor false, since we don't know).
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['reviewed'], None)

    def test_can_clear_reviewed_state(self):
        with session.begin():
            self.recipe.set_reviewed_state(self.owner, True)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'recipes/%s' % self.recipe.id,
                session=s, data={'reviewed': False})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.get_reviewed_state(self.owner), False)
