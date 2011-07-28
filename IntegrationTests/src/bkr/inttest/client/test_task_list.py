
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client

class TaskListTest(unittest.TestCase):

    def test_prints_names(self):
        task = data_setup.create_task()
        session.flush()
        out = run_client(['bkr', 'task-list'])
        self.assert_(task.name in out.splitlines(), out)

    # https://bugzilla.redhat.com/show_bug.cgi?id=720559
    def test_xml_works(self):
        task = data_setup.create_task()
        session.flush()
        out = run_client(['bkr', 'task-list', '--xml'])
        self.assert_('<task name="%s">\n\t<params/>\n</task>\n' % task.name
                in out, out)
