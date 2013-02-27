import unittest, datetime, os, threading
from bkr.server.model import TaskStatus, Job, System, User, \
        Group, SystemStatus, SystemActivity, Recipe, Cpu, LabController, \
        Provision
import sqlalchemy.orm
from sqlalchemy.sql import not_
from turbogears.database import session
import xmltramp
from bkr.server.jobxml import XmlJob
from bkr.inttest import data_setup
from bkr.inttest.assertions import assert_datetime_within, \
        assert_durations_not_overlapping
from bkr.server.tools import beakerd
from bkr.server.jobs import Jobs

class TestBeakerd(unittest.TestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)

    def test_loaned_machine_can_be_scheduled(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(status=u'Automated', shared=True,
                    lab_controller=self.lab_controller)
            # System has groups, which the user is not a member of, but is loaned to the user
            system.loaned = user
            data_setup.add_group_to_system(system, data_setup.create_group())
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)

    def test_reservations_are_created(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated',
                    shared=True, lab_controller=self.lab_controller)
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        beakerd.schedule_queued_recipes()

        with session.begin():
            job = Job.query.get(job.id)
            system = System.query.get(system.id)
            user = User.query.get(user.user_id)
            self.assertEqual(job.status, TaskStatus.scheduled)
            self.assertEqual(system.reservations[0].type, u'recipe')
            self.assertEqual(system.reservations[0].user, user)
            assert_datetime_within(system.reservations[0].start_time,
                    tolerance=datetime.timedelta(seconds=60),
                    reference=datetime.datetime.utcnow())
            self.assert_(system.reservations[0].finish_time is None)
            assert_durations_not_overlapping(system.reservations)

    def test_empty_and_element(self):
        with session.begin():
            user = data_setup.create_user()
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    u'<hostRequires><and></and></hostRequires>')

        beakerd.process_new_recipes()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)

    def test_or_lab_controller(self):
        with session.begin():
            user = data_setup.create_user()
            lc1 = data_setup.create_labcontroller(u'test_or_labcontroller.lab1')
            lc2 = data_setup.create_labcontroller(u'test_or_labcontroller.lab2')
            lc3 = data_setup.create_labcontroller(u'test_or_labcontroller.lab3')
            system1 = data_setup.create_system(arch=u'i386', shared=True)
            system1.lab_controller = lc1
            system2 = data_setup.create_system(arch=u'i386', shared=True)
            system2.lab_controller = lc2
            system3 = data_setup.create_system(arch=u'i386', shared=True)
            system3.lab_controller = lc3
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                   <hostRequires>
                    <or>
                     <hostlabcontroller op="=" value="test_or_labcontroller.lab1"/>
                     <hostlabcontroller op="=" value="test_or_labcontroller.lab2"/>
                    </or>
                   </hostRequires>
                   """)
            session.flush()
            job_id = job.id
            system1_id = system1.id
            system2_id = system2.id
            system3_id = system3.id

        beakerd.process_new_recipes()

        with session.begin():
            job = Job.query.get(job_id)
            system1 = System.query.get(system1_id)
            system2 = System.query.get(system2_id)
            system3 = System.query.get(system3_id)
            self.assertEqual(job.status, TaskStatus.processed)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(len(candidate_systems), 2)
            self.assert_(system1 in candidate_systems)
            self.assert_(system2 in candidate_systems)
            self.assert_(system3 not in candidate_systems)

    def check_user_cannot_run_job_on_system(self, user, system):
        """
        Asserts that the given user is not allowed to run a job against the 
        given system, i.e. that it aborts due to no matching systems.
        """
        with session.begin():
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.aborted)
        return job.id

    def check_user_can_run_job_on_system(self, user, system):
        """
        Asserts that the given user *is* allowed to run a job against the given 
        system, i.e. that it does not abort due to no matching systems. Inverse 
        of the method above.
        """
        with session.begin():
            job = data_setup.create_job(owner=user)
            job.recipesets[0].recipes[0]._host_requires = (
                    '<hostRequires><hostname op="=" value="%s"/></hostRequires>'
                    % system.fqdn)
        beakerd.process_new_recipes()
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.processed)
        return job.id

    def test_nonshared_system_not_owner(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False, owner=data_setup.create_user())
        self.check_user_cannot_run_job_on_system(user, system)

    def test_nonshared_system_owner(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False, owner=user)
        self.check_user_can_run_job_on_system(user, system)

    def test_nonshared_system_admin(self):
        with session.begin():
            admin = data_setup.create_admin()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=False)
        self.check_user_cannot_run_job_on_system(admin, system)

    def test_shared_system_not_owner(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
        self.check_user_can_run_job_on_system(user, system)

    def test_shared_system_admin(self):
        with session.begin():
            admin = data_setup.create_admin()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
        self.check_user_can_run_job_on_system(admin, system)

    def test_shared_group_system_with_user_not_in_group(self):
        with session.begin():
            user = data_setup.create_user()
            group = data_setup.create_group()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
            system.groups.append(group)
        self.check_user_cannot_run_job_on_system(user, system)

    def test_shared_group_system_with_user_in_group(self):
        with session.begin():
            group = data_setup.create_group()
            user = data_setup.create_user()
            user.groups.append(group)
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
            system.groups.append(group)
        self.check_user_can_run_job_on_system(user, system)

    def test_shared_group_system_with_admin_not_in_group(self):
        with session.begin():
            admin = data_setup.create_admin()
            group = data_setup.create_group()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
            system.groups.append(group)
        self.check_user_cannot_run_job_on_system(admin, system)

    def test_shared_group_system_with_admin_in_group(self):
        with session.begin():
            group = data_setup.create_group()
            admin = data_setup.create_admin()
            admin.groups.append(group)
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True)
            system.groups.append(group)
        self.check_user_can_run_job_on_system(admin, system)

    def test_loaned_system_with_admin(self):
        with session.begin():
            loanee = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, loaned=loanee)
            admin = data_setup.create_admin()
        job_id = self.check_user_can_run_job_on_system(admin, system)
        beakerd.queue_processed_recipesets()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.schedule_queued_recipes()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
            system = System.query.get(system.id)
            self.assertEqual(system.user, None)

    def test_loaned_system_with_loanee(self):
        with session.begin():
            loanee = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, loaned=loanee)
        job_id = self.check_user_can_run_job_on_system(loanee, system)
        beakerd.queue_processed_recipesets()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        beakerd.schedule_queued_recipes()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.scheduled)
            system = System.query.get(system.id)
            self.assertEqual(system.user.user_id, loanee.user_id)

    def test_loaned_system_with_not_loanee(self):
        with session.begin():
            loanee = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, loaned=loanee)
            user = data_setup.create_user()
        job_id = self.check_user_can_run_job_on_system(user, system)
        beakerd.queue_processed_recipesets()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.schedule_queued_recipes()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
            system = System.query.get(system.id)
            self.assertEqual(system.user, None)

    def test_loaned_system_with_owner(self):
        with session.begin():
            loanee = data_setup.create_user()
            owner = data_setup.create_user()
            system = data_setup.create_system(lab_controller=self.lab_controller,
                    shared=True, owner=owner, loaned=loanee)
        # owner of the system has access, when the
        # loan is returned their job will be able to run.
        job_id = self.check_user_can_run_job_on_system(owner, system)
        beakerd.queue_processed_recipesets()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
        # Even though the system is free the job should stay queued while
        # the loan is in place.
        beakerd.schedule_queued_recipes()
        with session.begin():
            job = Job.query.get(job_id)
            self.assertEqual(job.status, TaskStatus.queued)
            system = System.query.get(system.id)
            self.assertEqual(system.user, None)
    
    def test_fail_harness_repo(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated', shared=True,
                    lab_controller=self.lab_controller)
            job = data_setup.create_job(owner=user)
            recipe = job.recipesets[0].recipes[0]
            recipe._host_requires = (
                    u'<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        harness_dir = '%s/%s' % (recipe.harnesspath, \
            recipe.distro_tree.distro.osversion.osmajor)
        try:
            if os.path.exists(harness_dir):
                os.rmdir(harness_dir)
            beakerd.process_new_recipes()
            beakerd.queue_processed_recipesets()
            beakerd.schedule_queued_recipes()
            beakerd.provision_scheduled_recipesets()
            with session.begin():
                job = Job.by_id(job.id)
                self.assertEqual(job.status, TaskStatus.aborted)
        finally:
            if not os.path.exists(harness_dir):
                os.mkdir(harness_dir)
    
    def test_success_harness_repo(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system(owner=user, status=u'Automated',
                    shared=True, lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            job = data_setup.create_job(owner=user, distro_tree=distro_tree)
            recipe = job.recipesets[0].recipes[0]
            recipe._host_requires = (
                    '<hostRequires><and><hostname op="=" value="%s"/></and></hostRequires>'
                    % system.fqdn)

        harness_dir = '%s/%s' % (recipe.harnesspath, \
            recipe.distro_tree.distro.osversion.osmajor)

        if not os.path.exists(harness_dir):
            os.mkdir(harness_dir)
        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        beakerd.schedule_queued_recipes()
        beakerd.provision_scheduled_recipesets()
        with session.begin():
            job = Job.by_id(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)

    def test_single_processor_priority(self):
        with session.begin():
            user = data_setup.create_user()
            system_two_proc_owner = data_setup.create_system(
                lab_controller=self.lab_controller, owner=user, cpu=Cpu(processors=2))
            system_one_proc_owner = data_setup.create_system(
                lab_controller=self.lab_controller, owner=user, cpu=Cpu(processors=1))
            system_two_proc = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=2))
            system_one_proc = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=1))
            system_no_proc = data_setup.create_system(
                lab_controller=self.lab_controller)
            # Just in case we start adding CPUs by default to systems...
            system_no_proc.cpu = None

            recipe1 = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe1])
            job.owner = user
            recipe1.process()
            recipe1.queue()
            # Some fodder machines in here as well
            recipe1.systems[:] = [system_no_proc, system_one_proc,
                system_one_proc_owner, system_two_proc, system_two_proc_owner]
        beakerd.schedule_queued_recipe(recipe1.id)
        session.refresh(recipe1)
        # Test 2 proc > 1 proc within the owners
        self.assertEqual(recipe1.resource.system, system_two_proc_owner)

        # Test that non group, non owner single processor sorting works
        with session.begin():
            recipe2 = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe2])
            recipe2.process()
            recipe2.queue()
            recipe2.systems[:] = [system_one_proc, system_two_proc]
        beakerd.schedule_queued_recipe(recipe2.id)
        self.assertEqual(recipe2.resource.system, system_two_proc)

        # Test that group owner priority higher than dual processor
        with session.begin():
            recipe3 = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe3])
            system_two_proc_again = data_setup.create_system(
                lab_controller=self.lab_controller, cpu=Cpu(processors=2))
            job.owner = user
            recipe3.process()
            recipe3.queue()
            recipe3.systems[:] = [system_two_proc_again, system_one_proc_owner]
        beakerd.schedule_queued_recipe(recipe3.id)
        self.assertEqual(recipe3.resource.system, system_one_proc_owner)

    def test_successful_recipe_start(self):
        with session.begin():
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        beakerd.schedule_queued_recipes()
        beakerd.provision_scheduled_recipesets()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            self.assertEqual(system.command_queue[0].action, 'reboot')
            self.assertEqual(system.command_queue[1].action, 'configure_netboot')
            self.assertEqual(system.command_queue[2].action, 'clear_logs')

    # https://bugzilla.redhat.com/show_bug.cgi?id=880852
    def test_recipe_no_longer_has_access(self):
        with session.begin():
            group = data_setup.create_group()
            job_owner = data_setup.create_user()
            job_owner.groups.append(group)
            system1 = data_setup.create_system(shared=True,
                    fqdn='no_longer_has_access1',
                    lab_controller=self.lab_controller)
            system1.groups.append(group)
            system2 = data_setup.create_system(shared=True,
                    fqdn='no_longer_has_access2',
                    lab_controller=self.lab_controller)
            distro_tree = data_setup.create_distro_tree()
            job = data_setup.create_job(owner=job_owner, distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = u"""
                <hostRequires>
                    <or>
                        <hostname op="=" value="no_longer_has_access1" />
                        <hostname op="=" value="no_longer_has_access2" />
                    </or>
                </hostRequires>
                """
        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        with session.begin():
            job = Job.query.get(job.id)
            system1 = System.query.get(system1.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.queued)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(candidate_systems, [system1, system2])
            # now remove access to system1
            system1.groups[:] = [data_setup.create_group()]
        # first iteration: "recipe no longer has access"
        beakerd.schedule_queued_recipes()
        with session.begin():
            job = Job.query.get(job.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.queued)
            candidate_systems = job.recipesets[0].recipes[0].systems
            self.assertEqual(candidate_systems, [system2])
        # second iteration: system2 is picked instead
        beakerd.schedule_queued_recipes()
        with session.begin():
            job = Job.query.get(job.id)
            system2 = System.query.get(system2.id)
            self.assertEqual(job.status, TaskStatus.scheduled)
            picked_system = job.recipesets[0].recipes[0].resource.system
            self.assertEqual(picked_system, system2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=826379
    def test_recipe_install_options_can_remove_system_options(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            system = data_setup.create_system(shared=True,
                    lab_controller=self.lab_controller)
            system.provisions[distro_tree.arch] = Provision(arch=distro_tree.arch,
                    kernel_options='console=ttyS0 vnc')
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0].kernel_options = u'!vnc'
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        beakerd.schedule_queued_recipes()
        beakerd.provision_scheduled_recipesets()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.waiting)
            system = System.query.get(system.id)
            self.assertEqual(system.command_queue[1].action, 'configure_netboot')
            self.assert_('vnc' not in system.command_queue[1].kernel_options)

    def test_order_by(self):
        controller = Jobs()
        with session.begin():
            lab_controller = data_setup.create_labcontroller()

        with session.begin():
            distro_tree = data_setup.create_distro_tree()
            user = data_setup.create_admin()
            for x in range(0,3):
                data_setup.create_system(shared=True,
                        owner=user,
                        lab_controller=lab_controller)

        xmljob = XmlJob(xmltramp.parse("""
<job retention_tag="scratch">
	<whiteboard>
		
	</whiteboard>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Urgent">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Urgent">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
	<recipeSet priority="Normal">
		<recipe kernel_options="" kernel_options_post="" ks_meta="" role="RECIPE_MEMBERS" whiteboard="Normal">
			<autopick random="false"/>
			<watchdog/>
			<packages/>
			<ks_appends/>
			<repos/>
			<distroRequires>
				<and>
					<distro_family op="=" value="%(family)s"/>
					<distro_variant op="=" value="%(variant)s"/>
					<distro_name op="=" value="%(name)s"/>
					<distro_arch op="=" value="%(arch)s"/>
				</and>
			</distroRequires>
			<hostRequires>
				<hostlabcontroller op="=" value="%(labcontroller)s"/>
			</hostRequires>
			<partitions/>
			<task name="/distribution/reservesys" role="STANDALONE">
				<params/>
			</task>
		</recipe>
	</recipeSet>
</job>
                 """ % dict(labcontroller = lab_controller.fqdn,
                            family        = distro_tree.distro.osversion.osmajor,
                            variant       = distro_tree.variant,
                            name          = distro_tree.distro.name,
                            arch          = distro_tree.arch)))

        with session.begin():
            job = controller.process_xmljob(xmljob, user)

        beakerd.process_new_recipes()
        beakerd.queue_processed_recipesets()
        beakerd.schedule_queued_recipes()

        with session.begin():
            job = Job.query.get(job.id)
            for x in range(0,2):
                self.assertEqual(job.recipesets[x].recipes[0].status,
                                 TaskStatus.queued)
            for x in range(2,3):
                self.assertEqual(job.recipesets[x].recipes[0].status,
                                 TaskStatus.scheduled)
            for x in range(5,3):
                self.assertEqual(job.recipesets[x].recipes[0].status,
                                 TaskStatus.queued)

class FakeMetrics():
    def __init__(self):
        self.calls = []
    def measure(self, *args):
        self.calls.append(args)

class TestBeakerdMetrics(unittest.TestCase):

    def setUp(self):
        self.original_metrics = beakerd.metrics
        beakerd.metrics = FakeMetrics()
        session.begin()
        # Other tests might have left behind systems and running recipes,
        # so we remove or cancel them all so they don't pollute our metrics
        manually_reserved = System.query.filter(System.open_reservation != None)
        for system in manually_reserved:
            data_setup.unreserve_manual(system)
        systems = System.query.filter(System.status != SystemStatus.removed)
        for system in systems:
            system.status = SystemStatus.removed
        running = Recipe.query.filter(not_(Recipe.status.in_(
                [s for s in TaskStatus if s.finished])))
        for rs in running:
            rs.cancel()

    def tearDown(self):
        session.rollback()
        beakerd.metrics = self.original_metrics

    def test_system_count_metrics(self):
        gauges = [
            'gauges.systems_recipe',
            'gauges.systems_manual',
            'gauges.systems_idle_broken',
            'gauges.systems_idle_manual',
            'gauges.systems_idle_automated',
        ]
        categories = [
            'all',
            'shared',
            'by_arch.x86_64',
            'by_arch.i386',
            'by_arch.ppc',
            'by_arch.ppc64',
            'by_lab.checkmetrics_invalid_com',
        ]
        lc = data_setup.create_labcontroller(fqdn=u"checkmetrics.invalid.com")
        expected = dict(("%s.%s" % (g, c), 0)
                            for g in gauges for c in categories)
        for arch in u"i386 x86_64 ppc ppc64".split():
            data_setup.create_system(lab_controller=lc, arch=arch)
            data_setup.create_system(lab_controller=lc, arch=arch,
                                     status=SystemStatus.removed)
            categories = ['all', 'shared', 'by_lab.checkmetrics_invalid_com',
                          'by_arch.%s' % arch]
            for category in categories:
                key = 'gauges.systems_idle_automated.%s' % category
                expected[key] += 1
        # Ensure the test can cope with other systems showing
        # up as "idle_removed" in the metrics.
        lc = data_setup.create_labcontroller(fqdn=u"emptylab.invalid.com")
        data_setup.create_system(lab_controller=lc,
                                  status=SystemStatus.removed)
        session.flush()
        beakerd.system_count_metrics()
        # We need to split out unknown lab metrics, which we may inherit
        # from other tests which left systems in the database
        all_labs = {}
        known_metrics = {}
        other_labs = {}
        for k, v in beakerd.metrics.calls:
            all_labs[k] = v
            if k in expected:
                known_metrics[k] = v
            else:
                other_labs[k] = v
        self.assertEqual(set(known_metrics), set(expected))
        for k, v in known_metrics.iteritems():
            self.assertEqual((k, v), (k, expected[k]))
        for k, v in other_labs.iteritems():
            self.assertEqual((k, v), (k, 0))

    def test_recipe_count_metrics(self):
        gauges = [
            'gauges.recipes_scheduled',
            'gauges.recipes_running',
            'gauges.recipes_waiting',
            'gauges.recipes_processed',
            'gauges.recipes_new',
            'gauges.recipes_queued',
        ]
        categories = [
            'all',
            'dynamic_virt_possible',
            'by_arch.x86_64',
            'by_arch.i386',
            'by_arch.ppc',
            'by_arch.ppc64',
        ]
        expected = dict(("%s.%s" % (g, c), 0)
                            for g in gauges for c in categories)
        recipes = []
        for arch in u"i386 x86_64 ppc ppc64".split():
            dt = data_setup.create_distro_tree(arch=arch)
            job = data_setup.create_job(num_guestrecipes=1, distro_tree=dt)
            recipe = job.recipesets[0].recipes[0]
            recipes.append(recipe)
            categories = ['all', 'dynamic_virt_possible',
                          'by_arch.%s' % arch]
            for category in categories:
                key = 'gauges.recipes_new.%s' % category
                expected[key] += 1
        session.flush()
        beakerd.recipe_count_metrics()
        actual = dict(beakerd.metrics.calls)
        self.assertEqual(set(actual), set(expected))
        for k, v in actual.iteritems():
            self.assertEqual((k, v), (k, expected[k]))
        # Processing the recipes should set their virt status correctly
        for category in categories:
            new = 'gauges.recipes_new.%s' % category
            processed = 'gauges.recipes_processed.%s' % category
            if category != 'dynamic_virt_possible':
                expected[new], expected[processed] = 0, expected[new]
            else:
                # Possible virt candidates: i386, x86_64
                expected[new], expected[processed] = 0, 2
        for recipe in recipes:
            beakerd.process_new_recipe(recipe.id)
        beakerd.metrics.calls[:] = []
        beakerd.recipe_count_metrics()
        actual = dict(beakerd.metrics.calls)
