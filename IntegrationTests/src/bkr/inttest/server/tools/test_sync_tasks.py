import unittest2 as unittest
import os, shutil
from turbogears.database import session
from bkr.server.tools.sync_tasks import TaskLibrarySync
from bkr.server.model import Task
from bkr.inttest import get_server_base
import pkg_resources

class TestTaskLibrarySync(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_retrieve_tasks(self):
        task_sync = TaskLibrarySync(get_server_base())
        old_tasks, new_tasks = task_sync.tasks()
        with session.begin():
            tasks = Task.query.all()
            self.assertEqual(len(old_tasks), len(tasks))
            self.assertEqual(len(new_tasks), 0)

    def test_update_db(self):
        task_sync = TaskLibrarySync()
        # add a task to DB
        task_filename = 'task1.rpm'
        # task RPM in test dir
        test_task_rpm = pkg_resources.resource_filename(self.__module__, task_filename)
        # task RPM in the RPMs directory
        task_rpm_disk = os.path.join(task_sync.tasklib.rpmspath, task_filename)
        shutil.copyfile(test_task_rpm, task_rpm_disk)
        task_sync.tasks_added = [task_filename]
        task_sync.update_db()

        with session.begin():
            tasks = Task.query.filter(Task.rpm == task_filename).all()
            self.assertEqual(len(tasks), 1)

        self.assertTrue(os.path.exists(task_rpm_disk))

    def test_update_db_bad_task(self):
        task_sync = TaskLibrarySync()
        # add a task to DB
        task_filename = 'bad-task1.rpm'
        # task RPM in test dir
        test_task_rpm = pkg_resources.resource_filename(self.__module__, task_filename)
        # task RPM in the RPMs directory
        task_rpm_disk = os.path.join(task_sync.tasklib.rpmspath, task_filename)
        shutil.copyfile(test_task_rpm, task_rpm_disk)
        task_sync.tasks_added = [task_filename]
        task_sync.update_db()

        with session.begin():
            tasks = Task.query.filter(Task.rpm == task_filename).all()
            self.assertEqual(len(tasks), 0)

        self.assertTrue(not os.path.exists(task_rpm_disk))

    def test_bad_remote_task_download(self):
        task_sync = TaskLibrarySync()
        task_sync._download('http://remoteurl.invalid/task1.rpm')
        self.assertEqual(task_sync.t_downloaded, 0)
