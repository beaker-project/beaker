import unittest
from bkr.server.model import Job
from turbogears.database import session
from bkr.server.test import data_setup

class MaxWhiteboard(unittest.TestCase):

    def setUp(self):
        pass

    def test_max_whiteboard(self):
        max = Job.max_by_whiteboard
        jobs = []
        c = 0
        while c <= max:
            jobs.append(data_setup.create_job(whiteboard=u'thesame'))
            c += 1
        session.flush()
        jobs = Job.by_whiteboard(u'thesame')
        self.assert_(jobs.count() < 21 )


