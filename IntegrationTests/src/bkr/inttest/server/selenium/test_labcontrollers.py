
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import Distro, DistroTree, Arch, ImageType

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
