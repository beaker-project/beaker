
import os, os.path
import socket
import unittest
import tempfile
import random
import shutil
from bkr.labcontroller import netboot

def setUp():
    global tftp_root, orig_get_tftp_root, orig_gethostbyname
    tftp_root = tempfile.mkdtemp(prefix='test_netboot', suffix='tftproot')
    orig_get_tftp_root = netboot.get_tftp_root
    netboot.get_tftp_root = lambda: tftp_root
    orig_gethostbyname = socket.gethostbyname
    socket.gethostbyname = lambda hostname: '127.0.0.255'

def tearDown():
    netboot.get_tftp_root = orig_get_tftp_root
    socket.gethostbyname = orig_gethostbyname
    shutil.rmtree(tftp_root, ignore_errors=True)

class ImagesTest(unittest.TestCase):

    def setUp(self):
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
        netboot.fetch_images('file://%s' % self.kernel.name,
                'file://%s' % self.initrd.name,
                'fqdn.example.invalid')
        kernel_path = os.path.join(tftp_root, 'images', 'fqdn.example.invalid', 'kernel')
        initrd_path = os.path.join(tftp_root, 'images', 'fqdn.example.invalid', 'initrd')
        self.assert_(os.path.exists(kernel_path))
        self.assertEquals(os.path.getsize(kernel_path), 4 * 1024 * 1024)
        self.assert_(os.path.exists(initrd_path))
        self.assertEquals(os.path.getsize(initrd_path), 8 * 1024 * 1024)

        netboot.clear_images('fqdn.example.invalid')
        self.assert_(not os.path.exists(kernel_path))
        self.assert_(not os.path.exists(initrd_path))

class PxelinuxTest(unittest.TestCase):

    def test_configure_then_clear(self):
        netboot.configure_pxelinux('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        pxelinux_config_path = os.path.join(tftp_root, 'pxelinux.cfg', '7F0000FF')
        self.assertEquals(open(pxelinux_config_path).read(),
                '''default linux
prompt 0
timeout 100
label linux
    kernel /images/fqdn.example.invalid/kernel
    ipappend 2
    append initrd=/images/fqdn.example.invalid/initrd console=ttyS0,115200 ks=http://lol/
''')

        netboot.clear_pxelinux('fqdn.example.invalid')
        self.assert_(not os.path.exists(pxelinux_config_path))

    def test_multiple_initrds(self):
        netboot.configure_pxelinux('fqdn.example.invalid',
                'initrd=/mydriverdisk.img ks=http://lol/')
        pxelinux_config_path = os.path.join(tftp_root, 'pxelinux.cfg', '7F0000FF')
        self.assertEquals(open(pxelinux_config_path).read(),
                '''default linux
prompt 0
timeout 100
label linux
    kernel /images/fqdn.example.invalid/kernel
    ipappend 2
    append initrd=/images/fqdn.example.invalid/initrd,/mydriverdisk.img ks=http://lol/
''')

class EfigrubTest(unittest.TestCase):

    def test_configure_then_clear(self):
        netboot.configure_efigrub('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        grub_config_path = os.path.join(tftp_root, 'grub', '7F0000FF')
        self.assertEquals(open(grub_config_path).read(),
                '''default 0
timeout 10
title Beaker scheduled job for fqdn.example.invalid
    root (nd)
    kernel /images/fqdn.example.invalid/kernel console=ttyS0,115200 ks=http://lol/
    initrd /images/fqdn.example.invalid/initrd
''')

        netboot.clear_efigrub('fqdn.example.invalid')
        self.assert_(not os.path.exists(grub_config_path))

    def test_multiple_initrds(self):
        netboot.configure_efigrub('fqdn.example.invalid',
                'initrd=/mydriverdisk.img ks=http://lol/')
        grub_config_path = os.path.join(tftp_root, 'grub', '7F0000FF')
        self.assertEquals(open(grub_config_path).read(),
                '''default 0
timeout 10
title Beaker scheduled job for fqdn.example.invalid
    root (nd)
    kernel /images/fqdn.example.invalid/kernel ks=http://lol/
    initrd /images/fqdn.example.invalid/initrd /mydriverdisk.img
''')

class ZpxeTest(unittest.TestCase):

    def test_configure_then_clear(self):
        netboot.configure_zpxe('fqdn.example.invalid',
                # lots of options to test the 80-char wrapping
                'LAYER2=1 NETTYPE=qeth PORTNO=0 IPADDR=10.16.66.192 '
                'SUBCHANNELS=0.0.8000,0.0.8001,0.0.8002 MTU=1500 '
                'BROADCAST=10.16.71.255 SEARCHDNS= NETMASK=255.255.248.0 '
                'DNS=10.16.255.2 PORTNAME=z10-01 DASD=208C,218C,228C,238C '
                'GATEWAY=10.16.71.254 NETWORK=10.16.64.0 '
                'MACADDR=02:DE:AD:BE:EF:01 ks=http://lol/')
        self.assertEquals(open(os.path.join(tftp_root, 's390x',
                's_fqdn.example.invalid')).read(),
                '''/images/fqdn.example.invalid/kernel
/images/fqdn.example.invalid/initrd

''')
        self.assertEquals(open(os.path.join(tftp_root, 's390x',
                's_fqdn.example.invalid_parm')).read(),
                '''LAYER2=1 NETTYPE=qeth PORTNO=0 IPADDR=10.16.66.192 SUBCHANNELS=0.0.8000,0.0.8001
,0.0.8002 MTU=1500 BROADCAST=10.16.71.255 SEARCHDNS= NETMASK=255.255.248.0 DNS=1
0.16.255.2 PORTNAME=z10-01 DASD=208C,218C,228C,238C GATEWAY=10.16.71.254 NETWORK
=10.16.64.0 MACADDR=02:DE:AD:BE:EF:01 ks=http://lol/
''')
        self.assertEquals(open(os.path.join(tftp_root, 's390x',
                's_fqdn.example.invalid_conf')).read(),
                '')

        netboot.clear_zpxe('fqdn.example.invalid')
        self.assertEquals(open(os.path.join(tftp_root, 's390x',
                's_fqdn.example.invalid')).read(),
                'local\n')
        self.assert_(not os.path.exists(os.path.join(tftp_root, 's390x',
                's_fqdn.example.invalid_parm')))
        self.assert_(not os.path.exists(os.path.join(tftp_root, 's390x',
                's_fqdn.example.invalid_conf')))

class EliloTest(unittest.TestCase):

    def test_configure_then_clear(self):
        netboot.configure_elilo('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        elilo_config_path = os.path.join(tftp_root, '7F0000FF.conf')
        self.assertEquals(open(elilo_config_path).read(),
                '''relocatable

image=/images/fqdn.example.invalid/kernel
    label=netinstall
    append="console=ttyS0,115200 ks=http://lol/"
    initrd=/images/fqdn.example.invalid/initrd
    read-only
    root=/dev/ram
''')

        netboot.clear_elilo('fqdn.example.invalid')
        self.assert_(not os.path.exists(elilo_config_path))

class YabootTest(unittest.TestCase):

    def test_configure_then_clear(self):
        netboot.configure_yaboot('fqdn.example.invalid',
                'console=ttyS0,115200 ks=http://lol/')
        yaboot_config_path = os.path.join(tftp_root, 'etc', '7f0000ff')
        self.assertEquals(open(yaboot_config_path).read(),
                '''init-message="Beaker scheduled job for fqdn.example.invalid"
timeout=80
delay=10
default=linux

image=/images/fqdn.example.invalid/kernel
    label=linux
    initrd=/images/fqdn.example.invalid/initrd
    append="console=ttyS0,115200 ks=http://lol/"
''')
        yaboot_symlink_path = os.path.join(tftp_root, 'ppc', '7f0000ff')
        self.assertEquals(os.readlink(yaboot_symlink_path), '../yaboot')

        netboot.clear_yaboot('fqdn.example.invalid')
        self.assert_(not os.path.exists(yaboot_config_path))
        self.assert_(not os.path.exists(yaboot_symlink_path))
