
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class TaskListTest(ClientTestCase):

    def test_prints_names(self):
        with session.begin():
            task = data_setup.create_task()
        out = run_client(['bkr', 'task-list'])
        self.assert_(task.name in out.splitlines(), out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=720559
    def test_xml_works(self):
        with session.begin():
            task = data_setup.create_task()
        out = run_client(['bkr', 'task-list', '--xml'])
        self.assert_('<task name="%s">\n\t<params/>\n</task>\n' % task.name
                in out, out)

    def test_destructive_only(self):
        with session.begin():
            task1 = data_setup.create_task()
            task1.destructive = True
            task2 = data_setup.create_task()
            task2.destructive = False
        out = run_client(['bkr', 'task-list', '--destructive'])
        self.assert_(task1.name in out.splitlines(), out)
        self.assert_(task2.name not in out.splitlines(), out)

    def test_non_destructive_only(self):
        with session.begin():
            task1 = data_setup.create_task()
            task1.destructive = True
            task2 = data_setup.create_task()
            task2.destructive = False
        out = run_client(['bkr', 'task-list', '--non-destructive'])
        self.assert_(task1.name not in out.splitlines(), out)
        self.assert_(task2.name in out.splitlines(), out)

    def test_destructive_all(self):
        with session.begin():
            task1 = data_setup.create_task()
            task1.destructive = True
            task2 = data_setup.create_task()
            task2.destructive = False
        out = run_client(['bkr', 'task-list'])
        self.assert_(task1.name in out.splitlines(), out)
        self.assert_(task2.name in out.splitlines(), out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=728227
    def test_nonexistent_package(self):
        out = run_client(['bkr', 'task-list', '--package', 'notexist'])
        self.assertEquals(out, '')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1073280
    def test_by_distro(self):
        with session.begin():
            distro = data_setup.create_distro(osmajor=u'RedHatEnterpriseLinux6')
            included = data_setup.create_task()
            excluded = data_setup.create_task(
                    exclude_osmajors=[u'RedHatEnterpriseLinux6'])
        out = run_client(['bkr', 'task-list', '--distro', distro.name])
        task_names = out.splitlines()
        self.assertIn(included.name, task_names)
        self.assertNotIn(excluded.name, task_names)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1073280
    def test_nonexistent_distro(self):
        try:
            run_client(['bkr', 'task-list', '--distro', 'notexist'])
            self.fail('should raise')
        except ClientError as e:
            self.assertIn('No such distro: notexist', e.stderr_output)

    def test_task_list_by_type(self):
        with session.begin():
            task1 = data_setup.create_task(type=[u'Regression'])
            task2 = data_setup.create_task()
        out = run_client(['bkr', 'task-list', "--type=Regression"])
        self.assertIn(task1.name, out)
        self.assertNotIn(task2.name, out)

    def test_task_list_with_xml_params(self):
        with session.begin():
            task = data_setup.create_task()
        out = run_client(['bkr', 'task-list', '--xml', '--params', 'key=value'])
        self.assertIn('<task name="%s">'
                     '\n\t<params>\n\t\t<param name="key" value="value"/>\n\t</params>'
                     '\n</task>\n' % task.name, out)
