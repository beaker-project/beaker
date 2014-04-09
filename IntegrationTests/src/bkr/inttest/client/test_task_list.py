
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client

class TaskListTest(unittest.TestCase):

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
