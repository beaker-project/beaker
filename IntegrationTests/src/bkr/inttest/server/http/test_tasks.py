# encoding: utf8

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from sqlalchemy.sql import func
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as requests_login, patch_json
from bkr.server.database import session
from bkr.server.model import Task


class TaskHTTPTest(DatabaseTestCase):

    def setUp(self):
        super(TaskHTTPTest, self).setUp()
        with session.begin():
            self.my_task = data_setup.create_task()
            self.normal_user = data_setup.create_user(password=u'secret')

    def test_task_update_disable_successful(self):
        req_sess = requests.Session()
        requests_login(req_sess, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        self.assertEqual(self.my_task.valid, True)
        response = patch_json(get_server_base() + 'tasks/%s' % self.my_task.id,
                              session=req_sess, data={'disabled': True})
        response.raise_for_status()
        self.assertEqual(response.json()['valid'], False)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.my_task.valid, False)

    def test_task_update_disable_normal_user_fail(self):
        req_sess = requests.Session()
        requests_login(req_sess, self.normal_user.user_name, 'secret')
        self.assertEqual(self.my_task.valid, True)
        response = patch_json(get_server_base() + 'tasks/%s' % self.my_task.id,
                              session=req_sess, data={'disabled': True})
        self.assertEqual(response.status_code, 403)
        with session.begin():
            session.expire_all()
            self.assertEqual(self.my_task.valid, True)

    def test_task_update_task_not_available_404(self):
        req_sess = requests.Session()
        with session.begin():
            result = session.query(func.max(Task.id)).first()
        fake_id = result[0] + 1
        requests_login(req_sess, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        response = patch_json(get_server_base() + 'tasks/%s' % fake_id,
                              session=req_sess, data={'disabled': True})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.text, 'Task %s does not exist' % fake_id)
