import unittest
import datetime
from time import sleep
from bkr.server.model import TaskStatus, Job, System, User
import sqlalchemy.orm
from turbogears.database import session
from bkr.server.test import data_setup
from bkr.server.test.assertions import assert_datetime_within, \
        assert_durations_not_overlapping
from bkr.server.tools import beakerd
import threading

class TestBeakerd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        data_setup.create_test_env('min')
        session.flush()

    def _check_job_status(self, jobs, status):
        for j in jobs:
            job = Job.by_id(j.id)
            self.assertEqual(job.status,TaskStatus.by_name(status))

    def _create_cached_status(self):
        TaskStatus.by_name(u'Processed')
        TaskStatus.by_name(u'Queued')

    def test_cache_new_to_queued(self):
        jobs = list()
        distro = data_setup.create_distro()
        for i in range(30):
            job = data_setup.create_job(whiteboard=u'job_%s' % i, distro=distro)
            jobs.append(job)
        session.flush()
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
        self._check_job_status(jobs, u'Processed')

        thread_processed_recipe = Do(target=beakerd.processed_recipesets)
        thread_processed_recipe.start()
        thread_processed_recipe.join()
        self.assertTrue(thread_processed_recipe.success)
        session.clear()
        self._check_job_status(jobs, u'Queued')


    def test_loaned_machine_can_be_scheduled(self):
        user = data_setup.create_user()
        lc = data_setup.create_labcontroller()
        distro = data_setup.create_distro()
        system = data_setup.create_system(status=u'Automated', shared=True)
        system.lab_controller = lc
        # System has groups, which the user is not a member of, but is loaned to the user
        system.loaned = user
        data_setup.add_group_to_system(system, data_setup.create_group())
        job = data_setup.create_job(owner=user, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % system.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_reservations_are_created(self):
        data_setup.create_task(name=u'/distribution/install')
        user = data_setup.create_user()
        lc = data_setup.create_labcontroller()
        distro = data_setup.create_distro()
        system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        system.lab_controller = lc
        job = data_setup.create_job(owner=user, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                % system.fqdn)
        session.flush()
        session.clear()

        beakerd.new_recipes()
        beakerd.processed_recipesets()
        beakerd.queued_recipes()

        job = Job.query().get(job.id)
        system = System.query().get(system.id)
        user = User.query().get(user.user_id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Scheduled'))
        self.assertEqual(system.reservations[0].type, u'recipe')
        self.assertEqual(system.reservations[0].user, user)
        assert_datetime_within(system.reservations[0].start_time,
                tolerance=datetime.timedelta(seconds=60),
                reference=datetime.datetime.utcnow())
        self.assert_(system.reservations[0].finish_time is None)
        assert_durations_not_overlapping(system.reservations)

    def test_empty_and_element(self):
        data_setup.create_task(name=u'/distribution/install')
        user = data_setup.create_user()
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=user, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                u'<hostRequires><and></and></hostRequires>')
        session.flush()
        session.clear()

        beakerd.new_recipes()

        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_or_lab_controller(self):
        data_setup.create_task(name=u'/distribution/install')
        user = data_setup.create_user()
        lc1 = data_setup.create_labcontroller('lab1')
        lc2 = data_setup.create_labcontroller('lab2')
        lc3 = data_setup.create_labcontroller('lab3')
        distro = data_setup.create_distro()
        system1 = data_setup.create_system(arch=u'i386', shared=True)
        system1.lab_controller = lc1
        system2 = data_setup.create_system(arch=u'i386', shared=True)
        system2.lab_controller = lc2
        system3 = data_setup.create_system(arch=u'i386', shared=True)
        system3.lab_controller = lc3
        job = data_setup.create_job(owner=user, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (u"""
               <hostRequires>
                <or>
                 <hostlabcontroller op="=" value="lab1"/>
                 <hostlabcontroller op="=" value="lab2"/>
                </or>
               </hostRequires>
               """)
        session.flush()
        session.clear()

        beakerd.new_recipes()

        job = Job.query().get(job.id)
        system1 = System.query().get(system1.id)
        system2 = System.query().get(system2.id)
        system3 = System.query().get(system3.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))
        candidate_systems = job.recipesets[0].recipes[0].systems
        self.assertEqual(len(candidate_systems), 2)
        self.assert_(system1 in candidate_systems)
        self.assert_(system2 in candidate_systems)
        self.assert_(system3 not in candidate_systems)
