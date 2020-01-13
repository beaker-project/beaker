# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os, os.path
import socket
import unittest
import tempfile
import random
import shutil
from bkr.labcontroller import netboot
from bkr.common.helpers import makedirs_ignore

# This FQDN is embedded in a lot of the expected output for test cases
TEST_FQDN = 'fqdn.example.invalid'
TEST_ADDRESS = '127.0.0.255'

# Path maps
CONFIGURED_PATHS = {
    # These should exist after calling fetch_images or configure_<bootloader>
    "images": (
        ("images", TEST_FQDN, "kernel"),
        ("images", TEST_FQDN, "initrd"),
    ),
    "armlinux": (
        ("arm", "pxelinux.cfg", netboot.pxe_basename(TEST_ADDRESS)),
    ),
    "pxelinux": (
        ("pxelinux.cfg", netboot.pxe_basename(TEST_ADDRESS)),
    ),
    "ipxe": (
        ("ipxe", netboot.pxe_basename(TEST_ADDRESS).lower()),
    ),
    "efigrub": (
        ("grub", netboot.pxe_basename(TEST_ADDRESS)),
    ),
    "zpxe": (
        ("s390x", "s_%s_conf" % TEST_FQDN),
        ("s390x", "s_%s_parm" % TEST_FQDN),
    ),
    "elilo": (
        (netboot.pxe_basename(TEST_ADDRESS) + ".conf",),
    ),
    "yaboot": (
        ("etc", netboot.pxe_basename(TEST_ADDRESS).lower()),
        ("ppc", netboot.pxe_basename(TEST_ADDRESS).lower()),
    ),
}

PERSISTENT_PATHS = {
    # These exist even after calling clear_<bootloader>
    "armlinux": (
        ("arm", "empty"),
    ),
    "pxelinux": (
        ("pxelinux.cfg", "default"),
    ),
    "ipxe": (
        ("ipxe", "default"),
    ),
    "efigrub": (
        ("grub", "images"),
    ),
    "zpxe": (
        ("s390x", "s_%s" % TEST_FQDN),
    ),
}


class NetBootTestCase(unittest.TestCase):

    def setUp(self):
        self.tftp_root = tempfile.mkdtemp(prefix='test_netboot', suffix='tftproot')
        self.fake_conf = {
            'TFTP_ROOT': self.tftp_root,
        }
        self._orig_get_conf = netboot.get_conf
        netboot.get_conf = lambda: self.fake_conf
        self._orig_gethostbyname = socket.gethostbyname
        socket.gethostbyname = lambda hostname: TEST_ADDRESS

    def tearDown(self):
        netboot.get_conf = self._orig_get_conf
        socket.gethostbyname = self._orig_gethostbyname
        shutil.rmtree(self.tftp_root, ignore_errors=True)

    def check_netboot_absent(self, category):
        """Check state before calling fetch_images or configure_<bootloader>"""
        paths = self.make_filenames(CONFIGURED_PATHS[category])
        paths += self.make_filenames(PERSISTENT_PATHS.get(category, ()))
        for path in paths:
            self.assertFalse(os.path.lexists(path),
                             "Unexpected %r file: %r" % (category, path))

    def check_netboot_configured(self, category):
        """Check state after calling fetch_images or configure_<bootloader>"""
        paths = self.make_filenames(CONFIGURED_PATHS[category])
        paths += self.make_filenames(PERSISTENT_PATHS.get(category, ()))
        for path in paths:
            self.assertTrue(os.path.lexists(path),
                            "Missing %r file: %r" % (category, path))

    def check_netboot_cleared(self, category):
        """Check state after calling clear_<bootloader>"""
        paths = self.make_filenames(CONFIGURED_PATHS[category])
        for path in paths:
            self.assertFalse(os.path.lexists(path),
                             "Unexpected %r file: %r" % (category, path))
        persistent = self.make_filenames(PERSISTENT_PATHS.get(category, ()))
        for path in persistent:
            self.assertTrue(os.path.lexists(path),
                            "Missing persistent %r file: %r" %
                            (category, path))

    def check_netbootloader_leak(self, config):
        self.assertNotIn('netbootloader=', open(config).read())

    def make_filenames(self, paths):
        return [os.path.join(self.tftp_root, *parts) for parts in paths]


class LoaderImagesTest(NetBootTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=866765
    def test_pxelinux_is_populated(self):
        if not os.path.exists('/usr/share/syslinux'):
            raise unittest.SkipTest('syslinux is not installed')
        netboot.copy_default_loader_images()
        pxelinux_path = os.path.join(self.tftp_root, 'pxelinux.0')
        self.assertTrue(os.path.exists(pxelinux_path))
        menuc32_path = os.path.join(self.tftp_root, 'menu.c32')
        self.assertTrue(os.path.exists(menuc32_path))


class ImagesBaseTestCase(NetBootTestCase):

    def setUp(self):
        super(ImagesBaseTestCase, self).setUp()
        # make some dummy images
        self.kernel = tempfile.NamedTemporaryFile(prefix='test_netboot', suffix='kernel')
        for _ in xrange(4 * 1024):
            self.kernel.write(chr(random.randrange(0, 256)) * 1024)
        self.kernel.flush()
        self.initrd = tempfile.NamedTemporaryFile(prefix='test_netboot', suffix='initrd')
        for _ in xrange(8 * 1024):
            self.initrd.write(chr(random.randrange(0, 256)) * 1024)
        self.initrd.flush()


class ImagesTest(ImagesBaseTestCase):

    def test_fetch_then_clear(self):
        netboot.fetch_images(1234, 'file://%s' % self.kernel.name,
                             'file://%s' % self.initrd.name,
                             TEST_FQDN)
        self.check_netboot_configured("images")
        kernel_path = os.path.join(self.tftp_root, 'images', TEST_FQDN, 'kernel')
        initrd_path = os.path.join(self.tftp_root, 'images', TEST_FQDN, 'initrd')
        self.assertEquals(os.path.getsize(kernel_path), 4 * 1024 * 1024)
        self.assertEquals(os.path.getsize(initrd_path), 8 * 1024 * 1024)

        netboot.clear_images(TEST_FQDN)
        self.check_netboot_cleared("images")

    # https://bugzilla.redhat.com/show_bug.cgi?id=833662
    def test_fetch_twice(self):
        netboot.fetch_images(1234, 'file://%s' % self.kernel.name,
                             'file://%s' % self.initrd.name,
                             TEST_FQDN)
        netboot.fetch_images(1234, 'file://%s' % self.kernel.name,
                             'file://%s' % self.initrd.name,
                             TEST_FQDN)
        self.check_netboot_configured("images")
        kernel_path = os.path.join(self.tftp_root, 'images', TEST_FQDN, 'kernel')
        initrd_path = os.path.join(self.tftp_root, 'images', TEST_FQDN, 'initrd')
        self.assertEquals(os.path.getsize(kernel_path), 4 * 1024 * 1024)
        self.assertEquals(os.path.getsize(initrd_path), 8 * 1024 * 1024)


class ArchBasedConfigTest(ImagesBaseTestCase):
    common_categories = ("images", "armlinux", "efigrub",
                         "elilo", "yaboot", "pxelinux", "ipxe")

    def configure(self, arch):
        netboot.configure_all(TEST_FQDN, arch, 1234,
                              'file://%s' % self.kernel.name,
                              'file://%s' % self.initrd.name, "", self.tftp_root)

    def get_categories(self, arch):
        this = self.common_categories
        other = tuple(set(CONFIGURED_PATHS.keys()) - set(this))
        return this, other

    def check_configured(self, arch):
        categories, other = self.get_categories(arch)
        for category in categories:
            self.check_netboot_configured(category)
        for category in other:
            self.check_netboot_absent(category)

    def clear(self):
        netboot.clear_all(TEST_FQDN, self.tftp_root)

    def check_cleared(self, arch):
        categories, other = self.get_categories(arch)
        for category in categories:
            self.check_netboot_cleared(category)
        for category in other:
            self.check_netboot_absent(category)

    def test_configure_then_clear_common(self):
        arch = ""  # All common bootloaders are emitted for unknown arches
        self.configure(arch)
        self.check_configured(arch)
        self.clear()
        self.check_cleared(arch)


class PxelinuxTest(NetBootTestCase):

    def test_configure_symlink_then_clear(self):
        """
        Verify that kernel and initrd path points to images directory located in tftp root dir
        This is necessary in case of PXELINUX. PXELINUX is using relative paths from location
        of NBP instead of absolute paths as we can see in GRUB2.
        """
        bootloader_confs = os.path.join(self.tftp_root, 'bootloader', TEST_FQDN)
        netboot.configure_pxelinux(TEST_FQDN,
                                   'console=ttyS0,115200 ks=http://lol/',
                                   bootloader_confs,
                                   symlink=True)
        pxelinux_bootloader_path = os.path.join(
            self.tftp_root, 'bootloader', TEST_FQDN, 'pxelinux.cfg')
        pxelinux_config_path = os.path.join(pxelinux_bootloader_path, '7F0000FF')
        pxelinux_default_path = os.path.join(pxelinux_bootloader_path, 'default')
        open(pxelinux_config_path).readlines()
        self.assertEquals(open(pxelinux_config_path).read(),
                          '''default linux
prompt 0
timeout 100
label linux
    kernel ../../images/fqdn.example.invalid/kernel
    ipappend 2
    append initrd=../../images/fqdn.example.invalid/initrd console=ttyS0,115200 ks=http://lol/ netboot_method=pxe
''')
        self.assertEquals(open(pxelinux_default_path).read(),
                          '''default local
prompt 0
timeout 0
label local
    localboot 0
''')

        self.check_netbootloader_leak(pxelinux_config_path)
        netboot.clear_pxelinux(TEST_FQDN, bootloader_confs)
        self.assert_(not os.path.exists(pxelinux_config_path))

    def test_configure_then_clear(self):
        netboot.configure_pxelinux(TEST_FQDN,
                                   'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
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
        self.assertEquals(open(pxelinux_default_path).read(),
                          '''default local
prompt 0
timeout 0
label local
    localboot 0
''')
        self.check_netbootloader_leak(pxelinux_config_path)
        netboot.clear_pxelinux(TEST_FQDN, self.tftp_root)
        self.assert_(not os.path.exists(pxelinux_config_path))

    def test_multiple_initrds(self):
        netboot.configure_pxelinux(TEST_FQDN,
                                   'initrd=/mydriverdisk.img ks=http://lol/', self.tftp_root)
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1067924
    def test_kernel_options_are_not_quoted(self):
        netboot.configure_pxelinux(TEST_FQDN,
                                   'initrd=/mydriverdisk.img ks=http://example.com/~user/kickstart',
                                   self.tftp_root)
        pxelinux_config_path = os.path.join(self.tftp_root, 'pxelinux.cfg', '7F0000FF')
        config = open(pxelinux_config_path).read()
        self.assertIn('    append '
                      'initrd=/images/fqdn.example.invalid/initrd,/mydriverdisk.img '
                      'ks=http://example.com/~user/kickstart netboot_method=pxe',
                      config)

    def test_doesnt_overwrite_existing_default_config(self):
        pxelinux_dir = os.path.join(self.tftp_root, 'pxelinux.cfg')
        makedirs_ignore(pxelinux_dir, mode=0755)
        pxelinux_default_path = os.path.join(pxelinux_dir, 'default')
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
        netboot.configure_pxelinux(TEST_FQDN,
                                   'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        self.assertEquals(open(pxelinux_default_path).read(), custom)

class IpxeTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_ipxe(TEST_FQDN,
                'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        ipxe_config_path = os.path.join(self.tftp_root, 'ipxe', '7f0000ff')
        ipxe_default_path = os.path.join(self.tftp_root, 'ipxe', 'default')
        self.assertEquals(open(ipxe_config_path).read(),
                '''#!ipxe
kernel /images/fqdn.example.invalid/kernel
initrd /images/fqdn.example.invalid/initrd
imgargs kernel initrd=initrd console=ttyS0,115200 ks=http://lol/ netboot_method=ipxe BOOTIF=01-${netX/mac:hexhyp}
boot || exit 1
''')
        self.assertEquals(open(ipxe_default_path).read(),
                '''#!ipxe
iseq ${builtin/platform} pcbios && sanboot --no-describe --drive 0x80 ||
exit 1
''')
        self.check_netbootloader_leak(ipxe_config_path)
        netboot.clear_ipxe(TEST_FQDN, self.tftp_root)
        self.assert_(not os.path.exists(ipxe_config_path))

    def test_multiple_initrds(self):
        netboot.configure_ipxe(TEST_FQDN,
               'initrd=/mydriverdisk.img ks=http://lol/', self.tftp_root)
        ipxe_config_path = os.path.join(self.tftp_root, 'ipxe', '7f0000ff')
        self.assertEquals(open(ipxe_config_path).read(),
                '''#!ipxe
kernel /images/fqdn.example.invalid/kernel
initrd /images/fqdn.example.invalid/initrd
initrd /mydriverdisk.img
imgargs kernel initrd=initrd ks=http://lol/ netboot_method=ipxe BOOTIF=01-${netX/mac:hexhyp}
boot || exit 1
''')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1067924
    def test_kernel_options_are_not_quoted(self):
        netboot.configure_ipxe(TEST_FQDN,
                'initrd=/mydriverdisk.img ks=http://example.com/~user/kickstart', self.tftp_root)
        ipxe_config_path = os.path.join(self.tftp_root, 'ipxe', '7f0000ff')
        config = open(ipxe_config_path).read()
        self.assertIn('imgargs kernel initrd=initrd '
                'ks=http://example.com/~user/kickstart netboot_method=ipxe',
                config)

    def test_doesnt_overwrite_existing_default_config(self):
        ipxe_dir = os.path.join(self.tftp_root, 'ipxe')
        makedirs_ignore(ipxe_dir, mode=0755)
        ipxe_default_path = os.path.join(ipxe_dir, 'default')
        # in reality it will probably be a menu
        custom = '''#!ipxe
chain /ipxe/beaker_menu
exit 1
'''
        open(ipxe_default_path, 'wx').write(custom)
        netboot.configure_ipxe(TEST_FQDN,
               'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        self.assertEquals(open(ipxe_default_path).read(), custom)


class EfigrubTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_efigrub(TEST_FQDN,
                                  'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        grub_config_path = os.path.join(self.tftp_root, 'grub', '7F0000FF')
        self.assertEquals(open(grub_config_path).read(),
                          '''default 0
timeout 10
title Beaker scheduled job for fqdn.example.invalid
    root (nd)
    kernel /images/fqdn.example.invalid/kernel console=ttyS0,115200 ks=http://lol/ netboot_method=efigrub
    initrd /images/fqdn.example.invalid/initrd
''')
        self.check_netbootloader_leak(grub_config_path)
        netboot.clear_efigrub(TEST_FQDN, self.tftp_root)
        self.assert_(not os.path.exists(grub_config_path))

    def test_multiple_initrds(self):
        netboot.configure_efigrub(TEST_FQDN,
                                  'initrd=/mydriverdisk.img ks=http://lol/', self.tftp_root)
        grub_config_path = os.path.join(self.tftp_root, 'grub', '7F0000FF')
        self.assertEquals(open(grub_config_path).read(),
                          '''default 0
timeout 10
title Beaker scheduled job for fqdn.example.invalid
    root (nd)
    kernel /images/fqdn.example.invalid/kernel ks=http://lol/ netboot_method=efigrub
    initrd /images/fqdn.example.invalid/initrd /mydriverdisk.img
''')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1067924
    def test_kernel_options_are_not_quoted(self):
        netboot.configure_efigrub(TEST_FQDN,
                                  'initrd=/mydriverdisk.img ks=http://example.com/~user/kickstart',
                                  self.tftp_root)
        grub_config_path = os.path.join(self.tftp_root, 'grub', '7F0000FF')
        config = open(grub_config_path).read()
        self.assertIn('    kernel /images/fqdn.example.invalid/kernel '
                      'ks=http://example.com/~user/kickstart netboot_method=efigrub',
                      config)


class ZpxeTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_zpxe(TEST_FQDN,
                               'ftp://lab.example.invalid/kernel.img',
                               'ftp://lab.example.invalid/initrd.img',
                               # lots of options to test the 80-char wrapping
                               'LAYER2=1 NETTYPE=qeth PORTNO=0 IPADDR=10.16.66.192 '
                               'SUBCHANNELS=0.0.8000,0.0.8001,0.0.8002 MTU=1500 '
                               'BROADCAST=10.16.71.255 SEARCHDNS= NETMASK=255.255.248.0 '
                               'DNS=10.16.255.2 PORTNAME=z10-01 DASD=208C,218C,228C,238C '
                               'GATEWAY=10.16.71.254 NETWORK=10.16.64.0 '
                               'MACADDR=02:DE:AD:BE:EF:01 ks=http://lol/', self.tftp_root)
        self.assertEquals(open(os.path.join(self.tftp_root, 's390x',
                                            's_fqdn.example.invalid')).read(),
                          '''ftp://lab.example.invalid/kernel.img
ftp://lab.example.invalid/initrd.img

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
        netboot.clear_zpxe(TEST_FQDN, self.tftp_root)
        self.assertEquals(open(os.path.join(self.tftp_root, 's390x',
                                            's_fqdn.example.invalid')).read(),
                          'local\n')
        self.assert_(not os.path.exists(os.path.join(self.tftp_root, 's390x',
                                                     's_fqdn.example.invalid_parm')))
        self.assert_(not os.path.exists(os.path.join(self.tftp_root, 's390x',
                                                     's_fqdn.example.invalid_conf')))


class EliloTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_elilo(TEST_FQDN,
                                'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
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
        self.check_netbootloader_leak(elilo_config_path)
        netboot.clear_elilo(TEST_FQDN, self.tftp_root)
        self.assert_(not os.path.exists(elilo_config_path))


class YabootTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_yaboot(TEST_FQDN,
                                 'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
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
        self.check_netbootloader_leak(yaboot_config_path)
        netboot.clear_yaboot(TEST_FQDN, self.tftp_root)
        self.assert_(not os.path.exists(yaboot_config_path))
        self.assert_(not os.path.exists(yaboot_symlink_path))

    # https://bugzilla.redhat.com/show_bug.cgi?id=829984
    def test_configure_twice(self):
        netboot.configure_yaboot(TEST_FQDN,
                                 'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        netboot.configure_yaboot(TEST_FQDN,
                                 'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        yaboot_symlink_path = os.path.join(self.tftp_root, 'ppc', '7f0000ff')
        self.assertEquals(os.readlink(yaboot_symlink_path), '../yaboot')


class Grub2PPC64Test(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_ppc64(TEST_FQDN,
                                'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        grub2_configs_path = [os.path.join(self.tftp_root, 'ppc', 'grub.cfg-7F0000FF'),
                              os.path.join(self.tftp_root, 'boot', 'grub2', 'grub.cfg-7F0000FF'),
                              os.path.join(self.tftp_root, 'grub.cfg-7F0000FF')]
        for path in grub2_configs_path:
            self.assertEquals(open(path).read(), """\
linux  /images/fqdn.example.invalid/kernel console=ttyS0,115200 ks=http://lol/ netboot_method=grub2
initrd /images/fqdn.example.invalid/initrd

boot
""")
            self.check_netbootloader_leak(path)
        grub2_symlink_path = os.path.join(self.tftp_root, 'ppc', '7f0000ff-grub2')
        self.assertEquals(os.readlink(grub2_symlink_path),
                          '../boot/grub2/powerpc-ieee1275/core.elf')

        netboot.clear_ppc64(TEST_FQDN, self.tftp_root)
        for path in grub2_configs_path:
            self.assert_(not os.path.exists(path))
        self.assert_(not os.path.exists(grub2_symlink_path))


class Grub2TestX8664(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_x86_64(TEST_FQDN,
                                 'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        grub2_configs_path = [os.path.join(self.tftp_root, 'x86_64', 'grub.cfg-7F0000FF'),
                              os.path.join(self.tftp_root, 'boot', 'grub2', 'grub.cfg-7F0000FF')]
        grub2_default_path = [os.path.join(self.tftp_root, 'x86_64', 'grub.cfg'),
                              os.path.join(self.tftp_root, 'x86_64', 'grub.cfg')]

        for path in grub2_configs_path:
            self.assertEquals(open(path).read(), """\
linux  /images/fqdn.example.invalid/kernel console=ttyS0,115200 ks=http://lol/ netboot_method=grub2
initrd /images/fqdn.example.invalid/initrd

boot
""")
            self.check_netbootloader_leak(path)

        for path in grub2_default_path:
            self.assertEquals(open(path).read(), 'exit\n')

        netboot.clear_x86_64(TEST_FQDN, self.tftp_root)
        for path in grub2_configs_path:
            self.assert_(not os.path.exists(path))

        # Keep default
        for path in grub2_default_path:
            self.assert_(os.path.exists(path))


class Aarch64Test(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_aarch64(TEST_FQDN,
                                  'console=ttyS0,115200 ks=http://lol/', self.tftp_root)
        grub_config_path = os.path.join(self.tftp_root, 'aarch64', 'grub.cfg-7F0000FF')
        grub_default_path = os.path.join(self.tftp_root, 'aarch64', 'grub.cfg')
        self.assertEquals(open(grub_config_path).read(), """\
linux  /images/fqdn.example.invalid/kernel console=ttyS0,115200 ks=http://lol/ netboot_method=grub2
initrd /images/fqdn.example.invalid/initrd

boot
""")
        self.assertEquals(open(grub_default_path).read(), 'exit\n')
        self.check_netbootloader_leak(grub_config_path)
        netboot.clear_aarch64(TEST_FQDN, self.tftp_root)
        self.assertFalse(os.path.exists(grub_config_path))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1100008
    def test_alternate_devicetree(self):
        netboot.configure_aarch64(TEST_FQDN,
                                  'devicetree=custom.dtb ks=http://lol/', self.tftp_root)
        grub_config_path = os.path.join(self.tftp_root, 'aarch64', 'grub.cfg-7F0000FF')
        self.assertEquals(open(grub_config_path).read(), """\
linux  /images/fqdn.example.invalid/kernel ks=http://lol/ netboot_method=grub2
initrd /images/fqdn.example.invalid/initrd
devicetree custom.dtb
boot
""")


class PetitbootTest(NetBootTestCase):

    def test_configure_then_clear(self):
        netboot.configure_petitboot(TEST_FQDN,
                                    'ks=http://lol/ ksdevice=bootif', self.tftp_root)
        petitboot_config_path = os.path.join(self.tftp_root, 'bootloader',
                                             TEST_FQDN, 'petitboot.cfg')
        self.assertEquals(open(petitboot_config_path).read(), """\
default Beaker scheduled job for fqdn.example.invalid
label Beaker scheduled job for fqdn.example.invalid
kernel ::/images/fqdn.example.invalid/kernel
initrd ::/images/fqdn.example.invalid/initrd
append ks=http://lol/ ksdevice=bootif netboot_method=petitboot
""")
        self.check_netbootloader_leak(petitboot_config_path)
        netboot.clear_petitboot(TEST_FQDN, self.tftp_root)
        self.assertFalse(os.path.exists(petitboot_config_path))


class NetbootloaderTest(ImagesBaseTestCase):

    def test_configure_then_clear(self):
        netboot.configure_all(TEST_FQDN, 'ppc64', 1234,
                              'file://%s' % self.kernel.name,
                              'file://%s' % self.initrd.name,
                              'netbootloader=myawesome/netbootloader'
                              )
        bootloader_config_symlink = os.path.join(self.tftp_root, 'bootloader', TEST_FQDN, 'image')
        self.assertTrue(os.path.lexists(bootloader_config_symlink))
        self.assertEquals(os.path.realpath(bootloader_config_symlink),
                          os.path.join(self.tftp_root, 'myawesome/netbootloader'))
        # this tests ppc64 netboot creation
        grub2_config_file = os.path.join(self.tftp_root, 'bootloader', TEST_FQDN,
                                         'grub.cfg-7F0000FF')
        self.assertTrue(os.path.exists(grub2_config_file))
        self.check_netbootloader_leak(grub2_config_file)
        # Clear
        netboot.clear_netbootloader_directory(TEST_FQDN)

        # the FQDN directory is not removed
        self.assertTrue(os.path.exists(os.path.join(self.tftp_root, 'bootloader', TEST_FQDN)))
        # the image symlink is removed
        self.assertFalse(os.path.lexists(bootloader_config_symlink))
        # The config files for grub2 should be removed (since this is for PPC64)
        self.assertFalse(os.path.exists(grub2_config_file))
