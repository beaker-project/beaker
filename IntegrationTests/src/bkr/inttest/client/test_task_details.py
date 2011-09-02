
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client

class TaskDetailsTest(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=624417
    def test_details_include_owner_and_priority(self):
        owner = data_setup.create_user(user_name=u'besitzer@leo.org')
        task = data_setup.create_task(owner=owner, priority=u'Low')
        session.flush()
        out = run_client(['bkr', 'task-details', task.name])
        details = eval(out[len(task.name) + 1:]) # XXX dodgy
        self.assertEquals(details['owner'], u'besitzer@leo.org')
        self.assertEquals(details['priority'], u'Low')
