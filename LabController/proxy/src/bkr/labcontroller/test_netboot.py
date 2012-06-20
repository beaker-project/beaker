
import os, os.path
import socket
import unittest
import tempfile
import random
import shutil
from bkr.labcontroller import netboot

class NetBootTestCase(unittest.TestCase):

    def setUp(self):
        self.tftp_root = tempfile.mkdtemp(prefix='test_netboot', suffix='tftproot')
        self.fake_conf = {
            'TFTP_ROOT': self.tftp_root,
            'IMAGE_CACHE': True,
        }
        self._orig_get_conf = netboot.get_conf
        netboot.get_conf = lambda: self.fake_conf
        self._orig_gethostbyname = socket.gethostbyname
        socket.gethostbyname = lambda hostname: '127.0.0.255'

    def tearDown(self):
        netboot.get_conf = self._orig_get_conf
        socket.gethostbyname = self._orig_gethostbyname
        shutil.rmtree(self.tftp_root, ignore_errors=True)

class ImagesTest(NetBootTestCase):

    def setUp(self):
        super(ImagesTest, self).setUp()
        # make some dummy images
        self.kernel = tempfile.NamedTemporaryFile(prefix='test_netboot', suffix='kernel')
        for _ in xrange(4 * 1024):
            self.kernel.write(chr(random.randrange(0, 256)) * 1024)
        self.kernel.flush()
        self.initrd = tempfile.NamedTemporaryFile(prefix='test_netboot', suffix='initrd')
        for _ in xrange(8 * 1024):
            self.initrd.write(chr(random.randrange(0, 256)) * 1024)
        self.initrd.flush()

    def test_fetch_then_clear(self):
        netboot.fetch_images(1234, 'file://%s' % self.kernel.name,
                'file://%s' % self.initrd.name,
                'fqdn.example.invalid')
        kernel_path = os.path.join(self.tftp_root, 'images', 'fqdn.example.invalid', 'kernel')
        initrd_path = os.path.join(self.tftp_root, 'images', 'fqdn.example.invalid', 'initrd')
        self.assert_(os.path.exists(kernel_path))
        self.assertEquals(os.path.getsize(kernel_path), 4 * 1024 * 1024)
        self.assert_(os.path.exists(initrd_path))
        self.assertEquals(os.path.getsize(initrd_path), 8 * 1024 * 1024)

        netboot.clear_images('fqdn.example.invalid')
        self.assert_(not os.path.exists(kernel_path))
        self.assert_(not os.path.exists(initrd_path))

    # https://bugzilla.redhat.com/show_bug.cgi?id=833662
    def test_fetch_twice(self):
        netboot.fetch_images(1234, 'file://%s' % self.kernel.name,
                'file://%s' % self.initrd.name,
                'fqdn.example.invalid')
        netboot.fetch_images(1234, 'file://%s' % self.kernel.name,
                'file://%s' % self.initrd.name,
                'fqdn.example.invalid')
        kernel_path = os.path.join(self.tftp_root, 'images', 'fqdn.example.invalid', 'kernel')
        initrd_path = os.path.join(self.tftp_root, 'images', 'fqdn.example.invalid', 'initrd')
        self.assert_(os.path.exists(kernel_path))
        self.assertEquals(os.path.getsize(kernel_path), 4 * 1024 * 1024)
        self.assert_(os.path.exists(initrd_path))
        self.assertEquals(os.path.getsize(initrd_path), 8 * 1024 * 1024)

class PxelinuxTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_pxelinux('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        pxelinux_config_path = os.path.join(self.tftp_root, 'pxelinux.cfg', '7F0000FF')
        pxelinux_default_path = os.path.join(self.tftp_root, 'pxelinux.cfg', 'default')
        self.assertEquals(open(pxelinux_config_path).read(),
                '''default linux
prompt 0
timeout 100
label linux
    kernel /images/fqdn.example.invalid/kernel
    ipappend 2
    append initrd=/images/fqdn.example.invalid/initrd console=ttyS0,115200 ks=http://lol/ netboot_method=pxe
''')

        netboot.clear_pxelinux('fqdn.example.invalid')
        self.assert_(not os.path.exists(pxelinux_config_path))
        self.assertEquals(open(pxelinux_default_path).read(),
                '''default local
prompt 0
timeout 0
label local
    localboot 0
''')

    def test_multiple_initrds(self):
        netboot.configure_pxelinux('fqdn.example.invalid',
                'initrd=/mydriverdisk.img ks=http://lol/')
        pxelinux_config_path = os.path.join(self.tftp_root, 'pxelinux.cfg', '7F0000FF')
        self.assertEquals(open(pxelinux_config_path).read(),
                '''default linux
prompt 0
timeout 100
label linux
    kernel /images/fqdn.example.invalid/kernel
    ipappend 2
    append initrd=/images/fqdn.example.invalid/initrd,/mydriverdisk.img ks=http://lol/ netboot_method=pxe
''')

    def test_doesnt_overwrite_existing_default_config(self):
        netboot.configure_pxelinux('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        pxelinux_default_path = os.path.join(self.tftp_root, 'pxelinux.cfg', 'default')
        # in reality it will probably be a menu
        custom = '''
default local
prompt 10
timeout 200
label local
    localboot 0
label jabberwocky
    boot the thing'''
        open(pxelinux_default_path, 'wx').write(custom)
        netboot.clear_pxelinux('fqdn.example.invalid')
        self.assertEquals(open(pxelinux_default_path).read(), custom)

class EfigrubTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_efigrub('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        grub_config_path = os.path.join(self.tftp_root, 'grub', '7F0000FF')
        self.assertEquals(open(grub_config_path).read(),
                '''default 0
timeout 10
title Beaker scheduled job for fqdn.example.invalid
    root (nd)
    kernel /images/fqdn.example.invalid/kernel console=ttyS0,115200 ks=http://lol/ netboot_method=efigrub
    initrd /images/fqdn.example.invalid/initrd
''')

        netboot.clear_efigrub('fqdn.example.invalid')
        self.assert_(not os.path.exists(grub_config_path))

    def test_multiple_initrds(self):
        netboot.configure_efigrub('fqdn.example.invalid',
                'initrd=/mydriverdisk.img ks=http://lol/')
        grub_config_path = os.path.join(self.tftp_root, 'grub', '7F0000FF')
        self.assertEquals(open(grub_config_path).read(),
                '''default 0
timeout 10
title Beaker scheduled job for fqdn.example.invalid
    root (nd)
    kernel /images/fqdn.example.invalid/kernel ks=http://lol/ netboot_method=efigrub
    initrd /images/fqdn.example.invalid/initrd /mydriverdisk.img
''')

class ZpxeTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_zpxe('fqdn.example.invalid',
                # lots of options to test the 80-char wrapping
                'LAYER2=1 NETTYPE=qeth PORTNO=0 IPADDR=10.16.66.192 '
                'SUBCHANNELS=0.0.8000,0.0.8001,0.0.8002 MTU=1500 '
                'BROADCAST=10.16.71.255 SEARCHDNS= NETMASK=255.255.248.0 '
                'DNS=10.16.255.2 PORTNAME=z10-01 DASD=208C,218C,228C,238C '
                'GATEWAY=10.16.71.254 NETWORK=10.16.64.0 '
                'MACADDR=02:DE:AD:BE:EF:01 ks=http://lol/')
        self.assertEquals(open(os.path.join(self.tftp_root, 's390x',
                's_fqdn.example.invalid')).read(),
                '''/images/fqdn.example.invalid/kernel
/images/fqdn.example.invalid/initrd

''')
        self.assertEquals(open(os.path.join(self.tftp_root, 's390x',
                's_fqdn.example.invalid_parm')).read(),
                '''LAYER2=1 NETTYPE=qeth PORTNO=0 IPADDR=10.16.66.192 SUBCHANNELS=0.0.8000,0.0.8001
,0.0.8002 MTU=1500 BROADCAST=10.16.71.255 SEARCHDNS= NETMASK=255.255.248.0 DNS=1
0.16.255.2 PORTNAME=z10-01 DASD=208C,218C,228C,238C GATEWAY=10.16.71.254 NETWORK
=10.16.64.0 MACADDR=02:DE:AD:BE:EF:01 ks=http://lol/ netboot_method=zpxe
''')
        self.assertEquals(open(os.path.join(self.tftp_root, 's390x',
                's_fqdn.example.invalid_conf')).read(),
                '')

        netboot.clear_zpxe('fqdn.example.invalid')
        self.assertEquals(open(os.path.join(self.tftp_root, 's390x',
                's_fqdn.example.invalid')).read(),
                'local\n')
        self.assert_(not os.path.exists(os.path.join(self.tftp_root, 's390x',
                's_fqdn.example.invalid_parm')))
        self.assert_(not os.path.exists(os.path.join(self.tftp_root, 's390x',
                's_fqdn.example.invalid_conf')))

class EliloTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_elilo('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        elilo_config_path = os.path.join(self.tftp_root, '7F0000FF.conf')
        self.assertEquals(open(elilo_config_path).read(),
                '''relocatable

image=/images/fqdn.example.invalid/kernel
    label=netinstall
    append="console=ttyS0,115200 ks=http://lol/ netboot_method=elilo"
    initrd=/images/fqdn.example.invalid/initrd
    read-only
    root=/dev/ram
''')

        netboot.clear_elilo('fqdn.example.invalid')
        self.assert_(not os.path.exists(elilo_config_path))

class YabootTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_yaboot('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        yaboot_config_path = os.path.join(self.tftp_root, 'etc', '7f0000ff')
        self.assertEquals(open(yaboot_config_path).read(),
                '''init-message="Beaker scheduled job for fqdn.example.invalid"
timeout=80
delay=10
default=linux

image=/images/fqdn.example.invalid/kernel
    label=linux
    initrd=/images/fqdn.example.invalid/initrd
    append="console=ttyS0,115200 ks=http://lol/ netboot_method=yaboot"
''')
        yaboot_symlink_path = os.path.join(self.tftp_root, 'ppc', '7f0000ff')
        self.assertEquals(os.readlink(yaboot_symlink_path), '../yaboot')

        netboot.clear_yaboot('fqdn.example.invalid')
        self.assert_(not os.path.exists(yaboot_config_path))
        self.assert_(not os.path.exists(yaboot_symlink_path))

    # https://bugzilla.redhat.com/show_bug.cgi?id=829984
    def test_configure_twice(self):
        netboot.configure_yaboot('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        netboot.configure_yaboot('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        yaboot_symlink_path = os.path.join(self.tftp_root, 'ppc', '7f0000ff')
        self.assertEquals(os.readlink(yaboot_symlink_path), '../yaboot')
