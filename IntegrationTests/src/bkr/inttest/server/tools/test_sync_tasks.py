
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import subprocess
from bkr.inttest import Process
from turbogears.database import session
from bkr.common import __version__
from bkr.server.tools.sync_tasks import TaskLibrarySync
from bkr.server.model import Task
from bkr.inttest import get_server_base, DatabaseTestCase
from bkr.inttest.server.tools import run_command
import pkg_resources

_beaker_sync_tasks = pkg_resources.resource_filename('bkr.server.tools', 'sync_tasks.py')
_sync_tasks_dir = pkg_resources.resource_filename('bkr.inttest.server', 'task-rpms')
_http_server = pkg_resources.resource_filename('bkr.inttest', 'http_server.py')
_current_dir = os.path.dirname(__file__)
class TestTaskLibrarySync(DatabaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.task_server = Process('http_server.py',
                args=[sys.executable, _http_server, '--base', _sync_tasks_dir],
                listen_port=19998)
        cls.task_server.start()
        cls.task_url = 'http://localhost:19998/'

    @classmethod
    def tearDownClass(cls):
        cls.task_server.stop()

    def run_as_script(self, remote=None, debug=True, force=True):
        if not remote:
            remote = get_server_base()
        script_invocation = [sys.executable, _beaker_sync_tasks, '--remote', remote]
        if debug:
            script_invocation.append('--debug')
        if force:
            script_invocation.append('--force')
        p = subprocess.Popen(script_invocation,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        # sending 'y' is not required with --force, but
        # saves a new if..else block
        out, err = p.communicate('y')
        self.assertEquals('', err)

        return out

    def assertRegexpMatchesIn(self, text, items):
        for item in items:
            try:
                self.assertRegexpMatches(item, text)
            except AssertionError:
                continue
            else:
                return True

        return False

    def test_version(self):
        out = run_command('sync_tasks.py', 'beaker-sync-tasks', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_sync_two_tasks(self):
        task_sync = TaskLibrarySync()
        task_filename1 = 'task1.rpm'
        task_filename2 = 'task2.rpm'
        task_rpm_disk1 = os.path.join(task_sync.tasklib.rpmspath, task_filename1)
        task_rpm_disk2 = os.path.join(task_sync.tasklib.rpmspath, task_filename2)
        task_sync.sync_tasks(['%s%s' % (self.task_url, task_filename1),
            '%s%s' % (self.task_url, task_filename2)])

        with session.begin():
            tasks = Task.query.filter(Task.rpm == task_filename1).all()
            self.assertEqual(len(tasks), 1)
            tasks = Task.query.filter(Task.rpm == task_filename2).all()
            self.assertEqual(len(tasks), 1)

        self.assertTrue(os.path.exists(task_rpm_disk1))
        self.assertTrue(os.path.exists(task_rpm_disk2))

    def test_retrieve_tasks(self):
        task_sync = TaskLibrarySync(get_server_base())
        old_tasks, new_tasks = task_sync.tasks()
        with session.begin():
            tasks = Task.query.filter(Task.valid == True).all()
            self.assertEqual(len(old_tasks), len(tasks))
            self.assertEqual(len(new_tasks), 0)

    def test_sync_one_task(self):
        task_sync = TaskLibrarySync()
        task_filename = 'task4.rpm'
        task_rpm_disk = os.path.join(task_sync.tasklib.rpmspath, task_filename)
        task_sync.sync_tasks(['%s%s' % (self.task_url, task_filename)])

        with session.begin():
            tasks = Task.query.filter(Task.rpm == task_filename).all()
            self.assertEqual(len(tasks), 1)

        self.assertTrue(os.path.exists(task_rpm_disk))

    def test_invalid_task_rpm_is_not_synced(self):
        task_sync = TaskLibrarySync()
        # add a task to DB
        task_filename = 'bad-task1.rpm'
        # task RPM in test dir
        task_rpm_disk = os.path.join(task_sync.tasklib.rpmspath, task_filename)
        task_sync.sync_tasks(['%s%s' % (self.task_url, task_filename)])

        with session.begin():
            tasks = Task.query.filter(Task.rpm == task_filename).all()
            self.assertEqual(len(tasks), 0)

        self.assertFalse(os.path.exists(task_rpm_disk))

    def test_sync_two_tasks_one_fails(self):
        task_sync = TaskLibrarySync()
        task_sync.batch_size = 1
        good_task = 'task3.rpm'
        good_task_url = '%s%s' % (self.task_url, good_task)
        # We need this URL to end up sorted after the real one, hence 'x'
        bad_task = 'thisisnotreal.rpm'
        bad_task_url = '%s%s' % ('http://x.example.com/', bad_task)
        task_rpm_disk = os.path.join(task_sync.tasklib.rpmspath, good_task)
        try:
            task_sync.sync_tasks([good_task_url, bad_task_url])
        except Exception:
            pass
        with session.begin():
            tasks = Task.query.filter(Task.rpm == good_task).all()
            self.assertEqual(len(tasks), 1)

            tasks = Task.query.filter(Task.rpm == bad_task).all()
            self.assertEqual(len(tasks), 0)


        self.assertTrue(os.path.exists(task_rpm_disk))

    def test_script_run_log(self):

        remote = get_server_base()
        out = self.run_as_script(remote).splitlines()

        # Rough, but at least allows us to exercise the code path
        # we get the tasks from the local DB only which is not exactly how
        # it should be done - ideally we would be retrieving this task
        # list from both local DB and the remote server
        # However, here the remote server does not have a task which
        # is not present locally (vice-versa is not true), so it works for
        # us here
        with session.begin():
            tasks = Task.query.filter(Task.valid == True).all()
        for task in tasks:
            self.assertRegexpMatchesIn('Getting task XML for %s from %s' %
                               (task.name, remote.rstrip('/')), out)
            self.assertRegexpMatchesIn('Getting task XML for %s from local database' %
                                       task.name, out)

        # https://bugzilla.redhat.com/show_bug.cgi?id=1040226#c8
        out = self.run_as_script(remote, force=False).splitlines()
        self.assertRegexpMatchesIn('tasks already present may be overwritten' 
                                   'with the version from %s' % remote, out)
