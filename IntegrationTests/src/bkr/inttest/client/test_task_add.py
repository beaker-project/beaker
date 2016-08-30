
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import config
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase
import pkg_resources
from os import path
from bkr.server.model.tasklibrary import TaskLibrary


class TaskAddTest(ClientTestCase):

    def test_add_invalid_task(self):
        try:
            run_client(['bkr', 'task-add', '/dev/null'])
            fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assert_('error reading package header' in e.stderr_output,
                    e.stderr_output)

    def test_add_new_task_successfully(self):
        test_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                 'task-rpms/tmp-test-add-new-task-successfully.noarch.rpm')
        new_rpm = path.join(config.get('basepath.rpms'), 'tmp-test-add-new-task-successfully.noarch.rpm')
        out = run_client(['bkr', 'task-add', test_rpm])
        self.assertIn(u'Success', out)
        self.assertTrue(path.exists(new_rpm))

    def test_cannot_add_duplicate_tasks(self):
        import_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                 'task-rpms/tmp-test-cannot-add-duplicate-tasks-1.1.1-0.noarch.rpm')
        try:
            run_client(['bkr', 'task-add', import_rpm])
            # run this task-add twice to make duplicate error will show.
            run_client(['bkr', 'task-add', import_rpm])
            self.fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn('Cannot import duplicate task', e.stderr_output)

    def test_cannot_add_task_without_specifying_name(self):
        unde_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                 'task-rpms/empty.rpm')
        try:
            run_client(['bkr', 'task-add', unde_rpm])
            self.fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn('Name field not defined', e.stderr_output)


    def test_cannot_add_nonexistent_task(self):
        try:
            run_client(['bkr', 'task-add', '/non/exist/task.rpm'])
            self.fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn("No such file or directory:", e.stderr_output)


    def test_cannot_add_task_with_a_very_long_name(self):
        overlen_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                 'task-rpms/tmp-distribution-beaker-long-task-RPM-1.0-1.noarch.rpm')
        try:
            run_client(['bkr', 'task-add', overlen_rpm])
            self.fail('should  raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn('Task name should be <= 255 characters', e.stderr_output)


    def test_cannot_add_task_with_name_having_redundant_slashes(self):
        redundant_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                 'task-rpms/tmp-distribution-beaker----redundant_slashes-1.0-0.noarch.rpm')
        try:
            run_client(['bkr', 'task-add', redundant_rpm])
            self.fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn('Task name must not contain redundant slashes', e.stderr_output)


    def test_cannot_add_task_with_name_having_slash_end(self):
        slash_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                 'task-rpms/tmp-distribution-beaker-trailing_slash--1.0-0.noarch.rpm')
        try:
            run_client(['bkr', 'task-add', slash_rpm])
            self.fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn('Task name must not end with slash', e.stderr_output)

    def test_cannot_add_task_with_same_version(self):
        new_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                  'task-rpms/tmp-test-cannot-add-same-version-tasks-1.1.2-0.noarch.rpm')
        same_version_rpm = pkg_resources.resource_filename('bkr.inttest.server',
                                                  'task-rpms/tmp-test-cannot-add-same-version-1-tasks-1.1.2-0.noarch.rpm')
        try:
            run_client(['bkr', 'task-add', new_rpm])
            run_client(['bkr', 'task-add', same_version_rpm])
            self.fail('should raise')
        except ClientError, e:
            self.assertEqual(e.status, 1)
            self.assertIn('Failed to import,  1.1.2-0 is the same version we already have', e.stderr_output)