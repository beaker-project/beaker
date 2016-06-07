

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from bkr.server.model import session, RecipeTaskComment, RecipeTaskResultComment
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import post_json, login as requests_login

class RecipeTaskHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipe tasks.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.job = data_setup.create_job(owner=self.owner)
            self.recipe = self.job.recipesets[0].recipes[0]
            self.recipetask = self.recipe.tasks[0]

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

    def test_get_recipetask_comments(self):
        with session.begin():
            commenter = data_setup.create_user(user_name=u'peter')
            self.recipetask.comments.append(RecipeTaskComment(
                    user=commenter,
                    created=datetime.datetime(2015, 11, 5, 17, 0, 55),
                    comment=u'Microsoft and Red Hat to deliver new standard for '
                        u'enterprise cloud experiences'))
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/comments/' % (self.recipe.id, self.recipetask.id),
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(len(json['entries']), 1)
        self.assertEqual(json['entries'][0]['user']['user_name'], u'peter')
        self.assertEqual(json['entries'][0]['created'], u'2015-11-05 17:00:55')
        self.assertIn(u'Microsoft', json['entries'][0]['comment'])

    def test_post_recipetask_comment(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/comments/' % (self.recipe.id, self.recipetask.id),
                session=s, data={'comment': 'we unite on common solutions'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.recipetask.comments), 1)
            self.assertEqual(self.recipetask.comments[0].user, self.owner)
            self.assertEqual(self.recipetask.comments[0].comment,
                    u'we unite on common solutions')
            self.assertEqual(response.json()['id'],
                    self.recipetask.comments[0].id)

    def test_empty_comment_is_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/comments/' % (self.recipe.id, self.recipetask.id),
                session=s, data={'comment': None})
        self.assertEqual(response.status_code, 400)
        # whitespace-only comment also counts as empty
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/comments/' % (self.recipe.id, self.recipetask.id),
                session=s, data={'comment': ' '})
        self.assertEqual(response.status_code, 400)

    def test_anonymous_can_not_post_comment(self):
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/comments/' % (self.recipe.id, self.recipetask.id),
                data={'comment': 'testdata'})
        self.assertEqual(response.status_code, 401)

class RecipeTaskResultHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipe task results.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.job = data_setup.create_completed_job(owner=self.owner)
            self.recipe = self.job.recipesets[0].recipes[0]
            self.recipetask = self.recipe.tasks[0]
            self.result = self.recipetask.results[0]

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

    def test_get_recipe_task_result_comments(self):
        with session.begin():
            commenter = data_setup.create_user(user_name=u'adam')
            self.result.comments.append(RecipeTaskResultComment(
                    user=commenter,
                    created=datetime.datetime(2015, 11, 5, 17, 0, 55),
                    comment=u'Microsoft and Red Hat to deliver new standard for '
                        u'enterprise cloud experiences'))
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/comments/'
                % (self.recipe.id, self.recipetask.id, self.result.id),
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEqual(len(json['entries']), 1)
        self.assertEqual(json['entries'][0]['user']['user_name'], u'adam')
        self.assertEqual(json['entries'][0]['created'], u'2015-11-05 17:00:55')
        self.assertIn(u'Microsoft', json['entries'][0]['comment'])

    def test_post_recipe_task_result_comment(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/comments/'
                % (self.recipe.id, self.recipetask.id, self.result.id),
                session=s, data={'comment': 'we unite on common solutions'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(len(self.result.comments), 1)
            self.assertEqual(self.result.comments[0].user, self.owner)
            self.assertEqual(self.result.comments[0].comment,
                    u'we unite on common solutions')
            self.assertEqual(response.json()['id'],
                    self.result.comments[0].id)

    def test_empty_comment_is_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/comments/'
                % (self.recipe.id, self.recipetask.id, self.result.id),
                session=s, data={'comment': None})
        self.assertEqual(response.status_code, 400)
        # whitespace-only comment also counts as empty
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/comments/'
                % (self.recipe.id, self.recipetask.id, self.result.id),
                session=s, data={'comment': ' '})
        self.assertEqual(response.status_code, 400)

    def test_anonymous_can_not_post_comment(self):
        response = post_json(get_server_base() +
                'recipes/%s/tasks/%s/results/%s/comments/'
                % (self.recipe.id, self.recipetask.id, self.result.id),
                data={'comment': 'testdata'})
        self.assertEqual(response.status_code, 401)

    def test_404_response_to_string_rs_id(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = post_json(get_server_base() +
                 '/recipes/thisisnotanint/tasks/%s/comments/'
                 % self.recipe.tasks[0].id,
                 session=s, data={'comment': 'testdata'})
        self.assertEqual(response.status_code, 404)
