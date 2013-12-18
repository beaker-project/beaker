import unittest2 as unittest
import os
import shutil
import tempfile
from bkr.inttest import Process
from turbogears.database import session
from bkr.server.tools.sync_tasks import TaskLibrarySync
from bkr.server.model import Task
from bkr.inttest import get_server_base
import pkg_resources

_sync_tasks_dir = pkg_resources.resource_filename('bkr.inttest.server.tools', 'task_rpms')
_http_server = pkg_resources.resource_filename('bkr.inttest', 'http_server.py')
_current_dir = os.path.dirname(__file__)

class TestTaskLibrarySync(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        cls.task_server = Process('http_server.py',
                args=['python', _http_server,],
                listen_port=19998, exec_dir=_sync_tasks_dir)
        cls.task_server.start()
        cls.task_url = 'http://localhost:19998/'

    @classmethod
    def teardownClass(cls):
        cls.task_server.stop()

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
