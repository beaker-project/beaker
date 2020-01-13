
import sys
import os
import pkg_resources
import tempfile
import shutil
from bkr.server.model import session
from bkr.server.tests import data_setup
from bkr.inttest import Process
from bkr.inttest.labcontroller import LabControllerTestCase
from bkr.labcontroller.pxemenu import write_menus

class PxemenuTest(LabControllerTestCase):

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        # Need to populate a directory with fake images, and serve it over
        # HTTP, so that beaker-pxemenu can download the images when it builds
        # the menus.
        cls.distro_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(cls.distro_dir, 'pxeboot'))
        open(os.path.join(cls.distro_dir, 'pxeboot/vmlinuz'), 'w').write('lol')
        open(os.path.join(cls.distro_dir, 'pxeboot/initrd'), 'w').write('lol')
        cls.distro_server = Process('http_server.py', args=[sys.executable,
                    pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                    '--base', cls.distro_dir],
                listen_port=19998)
        cls.distro_server.start()
        cls.tftp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.distro_dir, ignore_errors=True)
        shutil.rmtree(cls.tftp_dir, ignore_errors=True)
        cls.distro_server.stop()

    def test_distro_tree_with_bad_url_throws_relevant_error(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_bad_url'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'SuperBadWindows10', osminor=u'1',
                    distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=[u'barf://localhost:19998/error/404'])
        with self.assertRaises(ValueError) as exc:
            write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        self.assertIn('Unrecognised URL scheme found in distro tree URL(s)', exc.exception.message)

    def test_skip_distro_tree_for_which_image_cannot_be_fetched(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_image_not_found'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'SuperBadWindows10', osminor=u'1',
                    distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=[u'http://localhost:19998/error/404'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'pxelinux.cfg', 'beaker_menu')).read()
        self.assertNotIn('menu title SuperBadWindows10', menu)
        menu = open(os.path.join(self.tftp_dir, 'ipxe', 'beaker_menu')).read()
        self.assertNotIn('menu SuperBadWindows10', menu)

    def test_pxelinux_menu(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_pxelinux_menu'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1-20140620.0', distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=[u'http://localhost:19998/'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'pxelinux.cfg', 'beaker_menu')).read()
        self.assertEquals(menu, '''\
default menu
prompt 0
timeout 6000
ontimeout local
menu title Beaker
label local
    menu label (local)
    menu default
    localboot 0

menu begin
menu title PinkUshankaLinux8

menu begin
menu title PinkUshankaLinux8.1

label PinkUshankaLinux8.1-20140620.0-Server-x86_64
    menu title PinkUshankaLinux8.1-20140620.0 Server x86_64
    kernel /distrotrees/{0}/kernel
    append initrd=/distrotrees/{0}/initrd method=http://localhost:19998/ repo=http://localhost:19998/ 

menu end

menu end
'''.format(distro_tree.id))

    def test_ipxe_menu(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_ipxe_menu'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1-20140620.42', distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=['http://localhost:19998/'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'ipxe', 'beaker_menu')).read()
        self.assertEquals(menu, '''\
#!ipxe

chain /ipxe/${ip:hexraw} ||

:main_menu
menu Beaker
item local (local)
item PinkUshankaLinux8 PinkUshankaLinux8 ->
choose --default local --timeout 600000 target && goto ${target} || goto local

:local
echo Booting local disk...
iseq ${builtin/platform} pcbios && sanboot --no-describe --drive 0x80 ||
# exit 1 generates an error message but req'd for some systems to fall through
exit 1 || goto main_menu

:PinkUshankaLinux8
menu PinkUshankaLinux8
item PinkUshankaLinux8.1 PinkUshankaLinux8.1 ->
item main_menu back <-
choose target && goto ${target} || goto main_menu

:PinkUshankaLinux8.1
menu PinkUshankaLinux8.1
item PinkUshankaLinux8.1-20140620.42-Server-x86_64 PinkUshankaLinux8.1-20140620.42 Server x86_64
item PinkUshankaLinux8 back <-
choose target && goto ${target} || goto PinkUshankaLinux8

:PinkUshankaLinux8.1-20140620.42-Server-x86_64
set options kernel initrd=initrd method=http://localhost:19998/ repo=http://localhost:19998/ 
echo Kernel command line: ${options}
prompt --timeout 5000 Press any key for additional options... && set opts 1 || clear opts
isset ${opts} && echo -n Additional options: ${} ||
isset ${opts} && read useropts ||
kernel /distrotrees/%s/kernel || goto PinkUshankaLinux8.1
initrd /distrotrees/%s/initrd || goto PinkUshankaLinux8.1
imgargs ${options} ${useropts}
boot || goto PinkUshankaLinux8.1

''' % (distro_tree.id, distro_tree.id))

    def test_efigrub_menu(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_efigrub_menu'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1-20140620.1', distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=[u'http://localhost:19998/'])
            # https://bugzilla.redhat.com/show_bug.cgi?id=1420471
            # i386 and RHEL3-5 should be filtered out
            ignored_combos = [
                (u'PinkUshankaLinux8', u'1', u'i386'),
                (u'RedHatEnterpriseLinux3', u'9', u'x86_64'),
                (u'RedHatEnterpriseLinux4', u'9', u'x86_64'),
                (u'RedHatEnterpriseLinuxServer5', u'10', u'x86_64'),
            ]
            for osmajor, osminor, arch in ignored_combos:
                data_setup.create_distro_tree(osmajor=osmajor, osminor=osminor,
                        arch=arch, distro_tags=[tag], lab_controllers=[lc],
                        urls=['http://localhost:19998/'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'grub', 'efidefault')).read()
        self.assertEquals(menu, '''\

title PinkUshankaLinux8.1-20140620.1 Server x86_64
    root (nd)
    kernel /distrotrees/{0}/kernel method=http://localhost:19998/ repo=http://localhost:19998/
    initrd /distrotrees/{0}/initrd
'''.format(distro_tree.id))

    def test_aarch64_menu(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_aarch64_menu'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1-20140620.2', distro_tags=[tag],
                    arch=u'aarch64', lab_controllers=[lc],
                    urls=[u'http://localhost:19998/'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'aarch64', 'beaker_menu.cfg')).read()
        self.assertEquals(menu, '''\
set default="Exit PXE"
set timeout=60
menuentry "Exit PXE" {
    exit
}

submenu "PinkUshankaLinux8" {

submenu "PinkUshankaLinux8.1" {

menuentry "PinkUshankaLinux8.1-20140620.2 Server aarch64" {
    linux /distrotrees/%s/kernel method=http://localhost:19998/ repo=http://localhost:19998/
    initrd /distrotrees/%s/initrd
}

}

}
''' % (distro_tree.id, distro_tree.id))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1087090
    def test_grub2_menu_for_efi(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_grub2_menu_for_efi'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1-20140620.3', distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=[u'http://localhost:19998/'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'boot', 'grub2',
            'beaker_menu_x86.cfg')).read()
        self.assertEquals(menu, '''\
set default="Exit PXE"
set timeout=60
menuentry "Exit PXE" {
    exit
}

submenu "PinkUshankaLinux8" {

submenu "PinkUshankaLinux8.1" {

menuentry "PinkUshankaLinux8.1-20140620.3 Server x86_64" {
    linux /distrotrees/%s/kernel method=http://localhost:19998/ repo=http://localhost:19998/
    initrd /distrotrees/%s/initrd
}

}

}
''' % (distro_tree.id, distro_tree.id))
