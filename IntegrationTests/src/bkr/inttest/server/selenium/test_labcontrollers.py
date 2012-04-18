
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import Distro, DistroTree, Arch, ImageType, Job, \
        System, SystemStatus, TaskStatus
from bkr.server.tools import beakerd

class AddDistroTreeXmlRpcTest(XmlRpcTestCase):

    distro_data = dict(
            name='RHEL-6-U1',
            arches=['i386', 'x86_64'], arch='x86_64',
            osmajor='RedHatEnterpriseLinux6', osminor='1',
            variant='Workstation', tree_build_time=1305067998.6483951,
            urls=['nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/',
                  'http://example.invalid/RHEL-6-Workstation/U1/x86_64/os/'],
            repos=[
                dict(repoid='Workstation', type='os', path=''),
                dict(repoid='ScalableFileSystem', type='addon', path='ScalableFileSystem/'),
                dict(repoid='optional', type='addon', path='../../optional/x86_64/os/'),
                dict(repoid='debuginfo', type='debug', path='../debug/'),
            ],
            images=[
                dict(type='kernel', path='images/pxeboot/vmlinuz'),
                dict(type='initrd', path='images/pxeboot/initrd.img'),
            ])

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
            self.lc2 = data_setup.create_labcontroller()
            self.lc2.user.password = u'logmein'
        self.server = self.get_server()

    def test_add_distro_tree(self):
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(self.distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            self.assertEquals(distro.osversion.osmajor.osmajor, u'RedHatEnterpriseLinux6')
            self.assertEquals(distro.osversion.osminor, u'1')
            self.assertEquals(distro.osversion.arches,
                    [Arch.by_name(u'i386'), Arch.by_name(u'x86_64')])
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs'),
                    'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.repo_by_id('Workstation').path,
                    '')
            self.assertEquals(distro_tree.repo_by_id('ScalableFileSystem').path,
                    'ScalableFileSystem/')
            self.assertEquals(distro_tree.repo_by_id('optional').path,
                    '../../optional/x86_64/os/')
            self.assertEquals(distro_tree.repo_by_id('debuginfo').path,
                    '../debug/')
            self.assertEquals(distro_tree.image_by_type(ImageType.kernel).path,
                    'images/pxeboot/vmlinuz')
            self.assertEquals(distro_tree.image_by_type(ImageType.initrd).path,
                    'images/pxeboot/initrd.img')
            self.assertEquals(distro_tree.activity[0].field_name, u'lab_controller_assocs')
            self.assertEquals(distro_tree.activity[0].action, u'Added')
            self.assert_(self.lc.fqdn in distro_tree.activity[0].new_value,
                    distro_tree.activity[0].new_value)
            del distro, distro_tree

        # another lab controller adds the same distro tree
        self.server.auth.login_password(self.lc2.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(self.distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.url_in_lab(self.lc2, scheme='nfs'),
                    'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.activity[0].field_name, u'lab_controller_assocs')
            self.assertEquals(distro_tree.activity[0].action, u'Added')
            self.assert_(self.lc2.fqdn in distro_tree.activity[0].new_value,
                    distro_tree.activity[0].new_value)
            del distro, distro_tree

    def test_change_url(self):
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.add_distro_tree(self.distro_data)

        # add it again, but with different urls
        new_distro_data = dict(self.distro_data)
        new_distro_data['urls'] = [
            # nfs:// is not included here, so it shouldn't change
            'nfs+iso://example.invalid:/RHEL-6-Workstation/U1/x86_64/iso/',
            'http://moved/',
        ]
        self.server.labcontrollers.add_distro_tree(new_distro_data)
        with session.begin():
            distro = Distro.by_name(u'RHEL-6-U1')
            distro_tree = DistroTree.query.filter_by(distro=distro,
                    variant=u'Workstation', arch=Arch.by_name('x86_64')).one()
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs'),
                    'nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/')
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='nfs+iso'),
                    'nfs+iso://example.invalid:/RHEL-6-Workstation/U1/x86_64/iso/')
            self.assertEquals(distro_tree.url_in_lab(self.lc, scheme='http'),
                    'http://moved/')
            del distro, distro_tree

class CommandQueueXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
        self.server = self.get_server()

    def test_obeys_max_running_commands_limit(self):
        with session.begin():
            for _ in xrange(15):
                system = data_setup.create_system(lab_controller=self.lc)
                system.action_power(action=u'on', service=u'testdata')
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        commands = self.server.labcontrollers.get_queued_command_details()
        # 10 is the configured limit in server-test.cfg
        self.assertEquals(len(commands), 10, commands)

class TestPowerFailures(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.lab_controller.user.password = u'logmein'
        self.server = self.get_server()
        self.server.auth.login_password(self.lab_controller.user.user_name,
                u'logmein')

    def test_automated_system_marked_broken(self):
        with session.begin():
            automated_system = data_setup.create_system(fqdn=u'broken1.example.org',
                                                        lab_controller=self.lab_controller,
                                                        status = SystemStatus.automated)
            command = automated_system.action_power(u'on')
        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')
        with session.begin():
            session.refresh(automated_system)
            self.assertEqual(automated_system.status, SystemStatus.broken)
            system_activity = automated_system.activity[0]
            self.assertEqual(system_activity.action, 'on')
            self.assertTrue(system_activity.new_value.startswith('Failed'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=720672
    def test_manual_system_status_not_changed(self):
        with session.begin():
            manual_system = data_setup.create_system(fqdn = u'broken2.example.org',
                                                     lab_controller = self.lab_controller,
                                                     status = SystemStatus.manual)
            command = manual_system.action_power(u'on')
        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')
        with session.begin():
            session.refresh(manual_system)
            self.assertEqual(manual_system.status, SystemStatus.manual)
            system_activity = manual_system.activity[0]
            self.assertEqual(system_activity.action, 'on')
            self.assertTrue(system_activity.new_value.startswith('Failed'))

    def test_broken_power_aborts_recipe(self):
        # Start a recipe, let it be provisioned, mark the power command as failed,
        # and the recipe should be aborted.
        with session.begin():
            system = data_setup.create_system(fqdn = u'broken.dreams.example.org',
                                              lab_controller = self.lab_controller,
                                              status = SystemStatus.automated,
                                              shared = True)
            distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora')
            job = data_setup.create_job(distro_tree=distro_tree)
            job.recipesets[0].recipes[0]._host_requires = (u"""
                <hostRequires>
                    <hostname op="=" value="%s" />
                </hostRequires>
                """ % system.fqdn)

        beakerd.new_recipes()
        beakerd.processed_recipesets()
        beakerd.queued_recipes()
        beakerd.scheduled_recipes()

        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.status, TaskStatus.running)
            system = System.query.get(system.id)
            command = system.command_queue[0]
            self.assertEquals(command.action, 'reboot')

        self.server.labcontrollers.mark_command_failed(command.id,
                u'needs moar powa')
        with session.begin():
            job = Job.query.get(job.id)
            self.assertEqual(job.recipesets[0].recipes[0].status,
                             TaskStatus.aborted)
