
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

    def test_pxelinux_menu(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_pxelinux_menu'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1', distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=['http://localhost:19998/'])
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

label PinkUshankaLinux8.1-Server-x86_64
    menu title PinkUshankaLinux8.1 Server x86_64
    kernel /distrotrees/{0}/kernel
    append initrd=/distrotrees/{0}/initrd method=http://localhost:19998/ repo=http://localhost:19998/ 

menu end

menu end
'''.format(distro_tree.id))

    def test_efigrub_menu(self):
        with session.begin():
            lc = self.get_lc()
            tag = u'test_efigrub_menu'
            distro_tree = data_setup.create_distro_tree(
                    osmajor=u'PinkUshankaLinux8', osminor=u'1',
                    distro_name=u'PinkUshankaLinux8.1', distro_tags=[tag],
                    arch=u'x86_64', lab_controllers=[lc],
                    urls=['http://localhost:19998/'])
        write_menus(self.tftp_dir, tags=[tag], xml_filter=None)
        menu = open(os.path.join(self.tftp_dir, 'grub', 'efidefault')).read()
        self.assertEquals(menu, '''\

title PinkUshankaLinux8.1 Server x86_64
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
                    distro_name=u'PinkUshankaLinux8.1', distro_tags=[tag],
                    arch=u'aarch64', lab_controllers=[lc],
                    urls=['http://localhost:19998/'])
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

menuentry "PinkUshankaLinux8.1 Server aarch64" {
    linux /distrotrees/%s/kernel method=http://localhost:19998/ repo=http://localhost:19998/
    initrd /distrotrees/%s/initrd
}

}

}
''' % (distro_tree.id, distro_tree.id))
