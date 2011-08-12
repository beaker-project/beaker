import unittest, datetime, os, threading
from time import sleep
from bkr.server.model import TaskStatus, Job, System, User, \
        Group, SystemStatus, SystemActivity, Recipe, LabController
import sqlalchemy.orm
from turbogears.database import session
from bkr.inttest import data_setup, stub_cobbler
from bkr.inttest.assertions import assert_datetime_within, \
        assert_durations_not_overlapping
from bkr.server.tools import beakerd

class TestBeakerd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        data_setup.create_test_env('min')
        cls.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        cls.stub_cobbler_thread.start()

        # create users
        cls.user_1 = data_setup.create_user()
        cls.user_2 = data_setup.create_user()
        cls.user_3 = data_setup.create_user()

        # create admin users
        cls.admin_1 = data_setup.create_user()
        cls.admin_1.groups.append(Group.by_name(u'admin'))
        cls.admin_2 = data_setup.create_user()
        cls.admin_2.groups.append(Group.by_name(u'admin'))

        # create systems
        cls.system_1 = data_setup.create_system(shared=True)
        cls.system_2 = data_setup.create_system(shared=True)
        cls.system_3 = data_setup.create_system(shared=False,
                                                 owner=cls.user_3)
        cls.system_4 = data_setup.create_system(shared=False,
                                                 owner=cls.user_3)

        # create group and add users/systems to it
        cls.group_1 = data_setup.create_group()
        cls.user_3.groups.append(cls.group_1)
        cls.admin_2.groups.append(cls.group_1)
        cls.system_2.groups.append(cls.group_1)

        # loan system_4 to user_1
        cls.system_4.loaned = cls.user_1

        lc = data_setup.create_labcontroller()
        cls.system_1.lab_controller = lc
        cls.system_2.lab_controller = lc
        cls.system_3.lab_controller = lc
        cls.system_4.lab_controller = lc

        session.flush()

    @classmethod
    def tearDownClass(cls):
        cls.stub_cobbler_thread.stop()

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
        lc1 = data_setup.create_labcontroller(u'lab1')
        lc2 = data_setup.create_labcontroller(u'lab2')
        lc3 = data_setup.create_labcontroller(u'lab3')
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

    def test_nonshared_system_3_user_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_3.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))

    def test_nonshared_system_3_user_3(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_3, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_3.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_nonshared_system_3_admin_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.admin_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_3.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))

    def test_shared_system_1_user_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_1.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_shared_system_1_admin_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.admin_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_1.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_shared_group_system_2_user_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_2.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))

    def test_shared_group_system_2_user_3(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_3, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_2.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_shared_group_system_2_admin_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.admin_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_2.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))

    def test_shared_group_system_2_admin_2(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.admin_2, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_2.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))

    def test_loaned_system_4_admin_1(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.admin_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_4.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))

    def test_loaned_system_4_user_1(self):
        print "user = %s" % self.user_1
        print "system = %s" % self.system_4
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_1, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_4.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))
        beakerd.processed_recipesets()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Queued'))
        beakerd.queued_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Scheduled'))
        system = System.query().get(self.system_4.id)
        self.assertEqual(system.user.user_id, self.user_1.user_id)
        # force the return of the system so that other tests will run 
        # correctly.
        system.user = None
        session.flush()

    def test_loaned_system_4_user_2(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_2, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_4.fqdn)
        session.flush()
        session.clear()
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))

    def test_loaned_system_4_user_3(self):
        distro = data_setup.create_distro()
        job = data_setup.create_job(owner=self.user_3, distro=distro)
        job.recipesets[0].recipes[0]._host_requires = (
                '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                % self.system_4.fqdn)
        session.flush()
        session.clear()
        # user_3 is the owner of the system so they have access, when the
        # loan is returned their job will be able to run.
        beakerd.new_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Processed'))
        beakerd.processed_recipesets()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Queued'))
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.queued_recipes()
        job = Job.query().get(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Queued'))
        system = System.query().get(self.system_4.id)
        self.assertEqual(system.user, None)
    
    def test_fail_harness_repo(self):

        lc = data_setup.create_labcontroller(fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        data_setup.create_task(name=u'/distribution/install')
        user = data_setup.create_user()
        distro = data_setup.create_distro()
        system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        system.lab_controller = lc
        job = data_setup.create_job(owner=user, distro=distro)
        recipe = job.recipesets[0].recipes[0]
        recipe._host_requires = (
                u'<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                % system.fqdn)

        harness_dir = '%s/%s' % (recipe.harnesspath, \
            recipe.distro.osversion.osmajor)
        try:
            if os.path.exists(harness_dir):
                os.rmdir(harness_dir)
            session.flush()
            beakerd.new_recipes()
            beakerd.processed_recipesets()
            beakerd.queued_recipes()

            for r in Recipe.query():
                if r.system:
                    r.system.lab_controller = lc
            beakerd.scheduled_recipes()
            job = Job.by_id(job.id)
            self.assertEqual(job.status, TaskStatus.by_name(u'Aborted'))
        finally:
            if not os.path.exists(harness_dir):
                os.mkdir(harness_dir)
    
    def test_success_harness_repo(self):

        lc = data_setup.create_labcontroller(fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        data_setup.create_task(name=u'/distribution/install')
        user = data_setup.create_user()
        distro = data_setup.create_distro()
        system = data_setup.create_system(owner=user, status=u'Automated', shared=True)
        system.lab_controller = lc
        job = data_setup.create_job(owner=user, distro=distro)
        recipe = job.recipesets[0].recipes[0]
        recipe._host_requires = (
                '<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                % system.fqdn)

        harness_dir = '%s/%s' % (recipe.harnesspath, \
            recipe.distro.osversion.osmajor)

        if not os.path.exists(harness_dir):
            os.mkdir(harness_dir)
        session.flush()
        beakerd.new_recipes()
        beakerd.processed_recipesets()
        beakerd.queued_recipes()
        lc = LabController.by_id(lc.id)
        for r in Recipe.query():
            if r.system:
                r.system.lab_controller = lc
        beakerd.scheduled_recipes()
        job = Job.by_id(job.id)
        self.assertEqual(job.status, TaskStatus.by_name(u'Running'))

class TestPowerFailures(unittest.TestCase):

    def setUp(self):
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.stub_cobbler_thread.start()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        session.flush()

    def tearDown(self):
        self.stub_cobbler_thread.stop()

    def test_automated_system_marked_broken(self):
        automated_system = data_setup.create_system(fqdn=u'broken1.example.org',
                                                    lab_controller=self.lab_controller,
                                                    status = SystemStatus.by_name(u'Automated'))
        automated_system.action_power(u'on')
        session.flush()
        session.clear()
        beakerd.queued_commands()
        beakerd.running_commands()
        automated_system = System.query().get(automated_system.id)
        self.assertEqual(automated_system.status, SystemStatus.by_name(u'Broken'))
        system_activity = automated_system.activity[0]
        self.assertEqual(system_activity.action, 'on')
        self.assertTrue(system_activity.new_value.startswith('Failed'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=720672
    def test_manual_system_status_not_changed(self):
        manual_system = data_setup.create_system(fqdn = u'broken2.example.org',
                                                 lab_controller = self.lab_controller,
                                                 status = SystemStatus.by_name(u'Manual'))
        manual_system.action_power(u'on')
        session.flush()
        session.clear()
        beakerd.queued_commands()
        beakerd.running_commands()
        manual_system = System.query().get(manual_system.id)
        self.assertEqual(manual_system.status, SystemStatus.by_name(u'Manual'))
        system_activity = manual_system.activity[0]
        self.assertEqual(system_activity.action, 'on')
        self.assertTrue(system_activity.new_value.startswith('Failed'))

    def test_mark_broken_updates_history(self):
        system = data_setup.create_system(status = SystemStatus.by_name(u'Automated'))
        system.mark_broken(reason = "Attacked by cyborgs")
        session.flush()
        session.clear()
        system = System.query().get(system.id)
        system_activity = system.dyn_activity.filter(SystemActivity.field_name == u'Status').first()
        self.assertEqual(system_activity.old_value, u'Automated')
        self.assertEqual(system_activity.new_value, u'Broken')
