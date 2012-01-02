
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.inttest import data_setup
from bkr.server.model import Distro, Arch

class AddDistroXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
            self.lc2 = data_setup.create_labcontroller()
            self.lc2.user.password = u'logmein'
        self.server = self.get_server()

    def test_register_new_distro(self):
        install_name = u'Fedora-42-x86_64'
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.register_distro(install_name)
        with session.begin():
            distro = Distro.by_install_name(install_name)
            self.assertEquals(distro.install_name, install_name)

    def test_register_existing_distro(self):
        install_name = u'Fedora-42-x86_64'
        with session.begin():
            distro = Distro(install_name=install_name)
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.register_distro(install_name)

    def test_add_distro(self):
        install_name = u'RHEL-6-U1-Workstation-x86_64'
        distro_data = dict(
                name=install_name, treename='RHEL-6-U1', breed='redhat',
                arches=['i386', 'x86_64'], arch='x86_64',
                osmajor='RedHatEnterpriseLinux6', osminor='1',
                variant='Workstation', tree_build_time=1305067998.6483951,
                ks_meta=dict(tree='nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/'))

        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        self.server.labcontrollers.register_distro(install_name)
        self.server.labcontrollers.add_distro(distro_data)
        with session.begin():
            distro = Distro.by_install_name(install_name)
            self.assertEquals(distro.name, u'RHEL-6-U1')
            self.assertEquals(distro.breed.breed, u'redhat')
            self.assertEquals(distro.arch, Arch.by_name(u'x86_64'))
            self.assertEquals(distro.osversion.osmajor.osmajor, u'RedHatEnterpriseLinux6')
            self.assertEquals(distro.osversion.osminor, u'1')
            self.assertEquals(distro.osversion.arches,
                    [Arch.by_name(u'i386'), Arch.by_name(u'x86_64')])
            self.assertEquals(distro.variant, u'Workstation')
            self.assert_(self.lc in distro.lab_controllers)
            self.assertEquals(distro.activity[0].field_name, u'lab_controllers')
            self.assertEquals(distro.activity[0].action, u'Added')
            self.assertEquals(distro.activity[0].new_value, self.lc.fqdn)
            del distro

        # another lab controller adds the same distro
        self.server.auth.login_password(self.lc2.user.user_name, u'logmein')
        self.server.labcontrollers.register_distro(install_name)
        self.server.labcontrollers.add_distro(distro_data)
        with session.begin():
            distro = Distro.by_install_name(install_name)
            print distro.activity
            self.assert_(self.lc2 in distro.lab_controllers)
            self.assertEquals(distro.activity[0].field_name, u'lab_controllers')
            self.assertEquals(distro.activity[0].action, u'Added')
            self.assertEquals(distro.activity[0].new_value, self.lc2.fqdn)
            del distro
