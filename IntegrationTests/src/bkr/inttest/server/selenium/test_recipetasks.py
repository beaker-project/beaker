

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase

class RecipeTaskHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipe tasks.
    """

    def test_get_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
            task = recipe.tasks[0]
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/logs/tasks/dummy.txt' % (recipe.id, task.id),
                allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/beaker/tasks/dummy.txt')

    def test_404_for_nonexistent_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
            task = recipe.tasks[0]
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/logs/doesnotexist.log' % (recipe.id, task.id),
                allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        self.assertRegexpMatches(response.text, 'Task log .* not found')

class RecipeTaskResultHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipe task results.
    """

    def test_get_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
            task = recipe.tasks[0]
            result = task.results[0]
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/logs/result.txt'
                % (recipe.id, task.id, result.id), allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/beaker/result.txt')

    def test_404_for_nonexistent_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
            task = recipe.tasks[0]
            result = task.results[0]
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/logs/doesnotexist.log'
                % (recipe.id, task.id, result.id), allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        self.assertRegexpMatches(response.text, 'Result log .* not found')
