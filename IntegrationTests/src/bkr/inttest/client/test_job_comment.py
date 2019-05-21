
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, \
    ClientError, ClientTestCase


class JobCommentTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        self.job = data_setup.create_completed_job()

    def test_invalid_taskpec(self):
        try:
            run_client(['bkr', 'job-comment', '12345'])
            self.fail('should raise')
        except ClientError as e:
            self.assertIn('Invalid taskspec', e.stderr_output)

    def test_post_comment_to_recipeset(self):
        with session.begin():
            recipe = self.job.recipesets[0]

        comment_text = u'Never gonna give you up'
        out = run_client(['bkr', 'job-comment', recipe.t_id,
                          '--message', comment_text])
        with session.begin():
            session.expire_all()
            self.assertEqual(recipe.comments[0].comment, comment_text)

    def test_post_comment_to_recipetask(self):
        with session.begin():
            recipe = self.job.recipesets[0].recipes[0]
            task = recipe.tasks[0]

        comment_text = u'Never gonna let you down'
        out = run_client(['bkr', 'job-comment', task.t_id,
                          '--message', comment_text])
        with session.begin():
            session.expire_all()
            self.assertEqual(task.comments[0].comment, comment_text)

    def test_post_comment_to_task_result(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_job_complete(job)
            result = recipe.tasks[0].results[0]

        comment_text = u'Never gonna run around and desert you'
        out = run_client(['bkr', 'job-comment', result.t_id,
                          '--message', comment_text])

        with session.begin():
            session.expire_all()
            self.assertEqual(result.comments[0].comment, comment_text)

    def test_anonymous_user_cannot_comment(self):
        with session.begin():
            client_config = create_client_config(username=None, password=None)

        comment_text = u'Never gonna make you cry'
        try:
            run_client(['bkr', 'job-comment', self.job.recipesets[0].t_id,
                        '--message', comment_text], config=client_config)
            self.fail('should raise')
        except ClientError as e:
            self.assertEquals(e.status, 1)
            self.assertIn('Invalid username or password', e.stderr_output)

    def test_empty_comment_is_rejected(self):
        try:
            run_client(['bkr', 'job-comment', self.job.recipesets[0].t_id,
                        '--message', ''])
            self.fail('should raise')
        except ClientError as e:
            self.assertIn('Comment text cannot be empty', e.stderr_output)

    def test_post_comment_on_multiple_taskspec(self):
        with session.begin():
            job = data_setup.create_completed_job()
            recipe1 = self.job.recipesets[0]
            recipe2 = job.recipesets[0]

        comment_text = u'Never gonna say goodbye'
        out = run_client(['bkr', 'job-comment', recipe1.t_id, recipe2.t_id,
                          '--message', comment_text])
        with session.begin():
            session.expire_all()
            self.assertEqual(recipe1.comments[0].comment, comment_text)
            self.assertEqual(recipe2.comments[0].comment, comment_text)

    def test_post_comment_to_tr_taskspec_string_fails(self):
        comment_text = u'Never gonna tell a lie...'
        try:
            run_client(['bkr', 'job-comment', 'TR:thisisnotanint', '--message',
                        comment_text])
            self.fail('should raise')
        except ClientError as e:
            self.assertIn('Recipe task result not found', e.stderr_output)
