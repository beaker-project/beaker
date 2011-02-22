import unittest

from time import sleep
from bkr.server.model import TaskStatus, Job
import sqlalchemy.orm
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.tools import beakerd
import threading

class TestBeakerd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        data_setup.create_test_env('min')
        session.flush()

    def setUp(self):
        self.jobs = list()
        distro = data_setup.create_distro()
        for i in range(30):
            job = data_setup.create_job(whiteboard=u'job_%s' % i, distro=distro)
            self.jobs.append(job)
        session.flush()

    def _check_job_status(self,status):
        for j in self.jobs:
            job = Job.by_id(j.id)
            self.assertEqual(job.status,TaskStatus.by_name(status))

    def _create_cached_status(self):
        TaskStatus.by_name(u'Processed')
        TaskStatus.by_name(u'Queued')

    def test_cache_new_to_queued(self):
        self._create_cached_status()

        #We need to run our beakerd methods as threads to ensure
        #that we have seperate sessions that create/read our cached object
        class Do(threading.Thread):
            def __init__(self,target,*args,**kw):
                super(Do,self).__init__(*args,**kw)
                self.target = target
            def run(self, *args, **kw):
                self.success = self.target()

        thread_new_recipe = Do(target=beakerd.new_recipes)

        thread_new_recipe.start()
        thread_new_recipe.join()
        self.assertTrue(thread_new_recipe.success)
        session.clear()
        self._check_job_status(u'Processed')

        thread_processed_recipe = Do(target=beakerd.processed_recipesets)
        thread_processed_recipe.start()
        thread_processed_recipe.join()
        self.assertTrue(thread_processed_recipe.success)
        session.clear()
        self._check_job_status(u'Queued')

    @classmethod
    def teardownClass(cls):
        pass
