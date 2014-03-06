
import os, os.path
import errno
import socket
import logging
import tempfile
import shutil
from contextlib import contextmanager
import collections
import urllib
import urllib2
from bkr.labcontroller.config import get_conf
from bkr.common.helpers import (atomically_replaced_file, makedirs_ignore,
        siphon, unlink_ignore, atomic_link, atomic_symlink)

logger = logging.getLogger(__name__)

def get_tftp_root():
    return get_conf().get('TFTP_ROOT', '/var/lib/tftpboot')

def write_ignore(path, content):
    """
    Creates and populates the given file, but leaves it untouched (and
    succeeds) if the file already exists.
    """
    try:
        f = open(path, 'wx') # not sure this is portable to Python 3!
    except IOError, e:
        if e.errno != errno.EEXIST:
            raise
    else:
        logger.debug("%s didn't exist, writing it", path)
        f.write(content)

def fetch_images(distro_tree_id, kernel_url, initrd_url, fqdn):
    """
    Creates references to kernel and initrd files at:

    <get_tftp_root()>/images/<fqdn>/kernel
    <get_tftp_root()>/images/<fqdn>/initrd
    """
    images_dir = os.path.join(get_tftp_root(), 'images', fqdn)
    makedirs_ignore(images_dir, 0755)
    distrotree_dir = os.path.join(get_tftp_root(), 'distrotrees', str(distro_tree_id))

    # beaker-pxemenu might have already fetched the images, so let's try there
    # before anywhere else.
    try:
        atomic_link(os.path.join(distrotree_dir, 'kernel'),
                os.path.join(images_dir, 'kernel'))
        atomic_link(os.path.join(distrotree_dir, 'initrd'),
                os.path.join(images_dir, 'initrd'))
        logger.debug('Using images from distro tree %s for %s', distro_tree_id, fqdn)
        return
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise
    # No luck there, so try something else...

    logger.debug('Fetching kernel %s for %s', kernel_url, fqdn)
    with atomically_replaced_file(os.path.join(images_dir, 'kernel')) as dest:
        siphon(urllib2.urlopen(kernel_url), dest)
    logger.debug('Fetching initrd %s for %s', initrd_url, fqdn)
    with atomically_replaced_file(os.path.join(images_dir, 'initrd')) as dest:
        siphon(urllib2.urlopen(initrd_url), dest)

def have_images(fqdn):
    return os.path.exists(os.path.join(get_tftp_root(), 'images', fqdn))

def clear_images(fqdn):
    """Removes kernel and initrd images """
    images_dir = os.path.join(get_tftp_root(), 'images', fqdn)
    logger.debug('Removing images for %s', fqdn)
    shutil.rmtree(images_dir, ignore_errors=True)

def pxe_basename(fqdn):
    # pxelinux uses upper-case hex IP address for config filename
    ipaddr = socket.gethostbyname(fqdn)
    return '%02X%02X%02X%02X' % tuple(int(octet) for octet in ipaddr.split('.'))

# Unfortunately the initrd kernel arg needs some special handling. It can be
# supplied from the Beaker side (e.g. a system-specific driver disk) but we
# also supply the main initrd here which we have fetched from the distro.
def extract_initrd_arg(kernel_options):
    """
    Returns a tuple of (initrd arg value, rest of kernel options). If there was
    no initrd= arg, the result will be (None, untouched kernel options).
    """
    initrd = None
    tokens = []
    for token in kernel_options.split():
        if token.startswith('initrd='):
            initrd = token[len('initrd='):]
        else:
            tokens.append(token)
    if initrd:
        return (initrd, ' '.join(tokens))
    else:
        return (None, kernel_options)

### Bootloader config: PXE Linux for aarch64

def configure_aarch64(fqdn, kernel_options):
    """
    Creates PXE bootloader files for aarch64 Linux

    <get_tftp_root()>/pxelinux/grub.cfg-<pxe_basename(fqdn)>

    Also ensures <fqdn>.efi is symlinked to bootaa64.efi

    Specify filename "pxelinux/<fqdn>.efi"; in your dhcpd.conf file
    We remove this when the install is done.  This allows efi
    to fall through to the next boot entry.
    """
    pxe_base = os.path.join(get_tftp_root(), 'pxelinux')
    makedirs_ignore(pxe_base, mode=0755)
    basename = "grub.cfg-%s" % pxe_basename(fqdn)
    config = '''  linux  ../images/%s/kernel %s
  initrd ../images/%s/initrd
  devicetree /pxelinux/apm-mustang.dtb
  boot
''' % (fqdn, kernel_options, fqdn)
    logger.debug('Writing aarch64 config for %s as %s', fqdn, basename)
    with atomically_replaced_file(os.path.join(pxe_base, basename)) as f:
        f.write(config)
    atomic_symlink('bootaa64.efi', os.path.join(pxe_base, "%s.efi" % fqdn))

def clear_aarch64(fqdn):
    """
    Removes PXE bootloader file created by configure_aarch64
    """
    pxe_base = os.path.join(get_tftp_root(), 'pxelinux')
    basename = "grub.cfg-%s" % pxe_basename(fqdn)
    logger.debug('Removing aarch64 config for %s as %s', fqdn, basename)
    unlink_ignore(os.path.join(pxe_base, "%s.efi" % fqdn))
    unlink_ignore(os.path.join(pxe_base, basename))
    # XXX Should we save a default config, the way we do for non-aarch64 PXE?


### Bootloader config: PXE Linux for ARM

def configure_armlinux(fqdn, kernel_options):
    """
    Creates PXE bootloader files for ARM Linux

    <get_tftp_root()>/arm/pxelinux.cfg/<pxe_basename(fqdn)>

    Also ensures empty config file exists:

    <get_tftp_root()>/arm/empty

    Specify filename "arm/empty"; in your dhcpd.conf file
    This is needed to set a path prefix of arm so that we don't
    conflict with x86 pxelinux.cfg files.
    """
    pxe_base = os.path.join(get_tftp_root(), 'arm')
    makedirs_ignore(pxe_base, mode=0755)
    write_ignore(os.path.join(pxe_base, 'empty'), '')
    pxe_dir = os.path.join(pxe_base, 'pxelinux.cfg')
    makedirs_ignore(pxe_dir, mode=0755)

    basename = pxe_basename(fqdn)
    config = '''default linux
prompt 0
timeout 100
label linux
    kernel ../images/%s/kernel
    initrd ../images/%s/initrd
    append %s netboot_method=armpxe
''' % (fqdn, fqdn, kernel_options)
    logger.debug('Writing armlinux config for %s as %s', fqdn, basename)
    with atomically_replaced_file(os.path.join(pxe_dir, basename)) as f:
        f.write(config)

def clear_armlinux(fqdn):
    """
    Removes PXE bootloader file created by configure_armlinux
    """
    pxe_dir = os.path.join(get_tftp_root(), 'arm', 'pxelinux.cfg')
    basename = pxe_basename(fqdn)
    logger.debug('Removing armlinux config for %s as %s', fqdn, basename)
    unlink_ignore(os.path.join(pxe_dir, basename))
    # XXX Should we save a default config, the way we do for non-ARM PXE?


### Bootloader config: PXE Linux

def configure_pxelinux(fqdn, kernel_options):
    """
    Creates PXE bootloader files for PXE Linux

    <get_tftp_root()>/pxelinux.cfg/<pxe_basename(fqdn)>

    Also ensures default (localboot) config exists:

    <get_tftp_root()>/pxelinux.cfg/default
    """
    pxe_dir = os.path.join(get_tftp_root(), 'pxelinux.cfg')
    makedirs_ignore(pxe_dir, mode=0755)

    basename = pxe_basename(fqdn)
    initrd, kernel_options = extract_initrd_arg(kernel_options)
    if initrd:
        initrd = '/images/%s/initrd,%s' % (fqdn, initrd)
    else:
        initrd = '/images/%s/initrd' % fqdn
    config = '''default linux
prompt 0
timeout 100
label linux
    kernel /images/%s/kernel
    ipappend 2
    append initrd=%s %s netboot_method=pxe
''' % (fqdn, initrd, kernel_options)
    logger.debug('Writing pxelinux config for %s as %s', fqdn, basename)
    with atomically_replaced_file(os.path.join(pxe_dir, basename)) as f:
        f.write(config)
    # We also ensure a default config exists that falls back to local boot
    write_ignore(os.path.join(pxe_dir, 'default'), '''default local
prompt 0
timeout 0
label local
    localboot 0
''')

def clear_pxelinux(fqdn):
    """
    Removes PXE bootloader file created by configure_pxelinux
    """
    pxe_dir = os.path.join(get_tftp_root(), 'pxelinux.cfg')
    basename = pxe_basename(fqdn)
    configname = os.path.join(pxe_dir, basename)
    logger.debug('Removing pxelinux config for %s as %s', fqdn, basename)
    unlink_ignore(configname)


### Bootloader config: EFI GRUB

def configure_efigrub(fqdn, kernel_options):
    """
    Creates bootloader file for EFI GRUB

    <get_tftp_root()>/grub/<pxe_basename(fqdn)>

    Also ensures images symlink exists:

    <get_tftp_root()>/grub/images -> <get_tftp_root()>/images
    """
    grub_dir = os.path.join(get_tftp_root(), 'grub')
    makedirs_ignore(grub_dir, mode=0755)
    atomic_symlink('../images', os.path.join(grub_dir, 'images'))

    basename = pxe_basename(fqdn)
    initrd, kernel_options = extract_initrd_arg(kernel_options)
    if initrd:
        initrd = ' '.join(['/images/%s/initrd' % fqdn] + initrd.split(','))
    else:
        initrd = '/images/%s/initrd' % fqdn
    config = '''default 0
timeout 10
title Beaker scheduled job for %s
    root (nd)
    kernel /images/%s/kernel %s netboot_method=efigrub
    initrd %s
''' % (fqdn, fqdn, kernel_options, initrd)
    logger.debug('Writing grub config for %s as %s', fqdn, basename)
    with atomically_replaced_file(os.path.join(grub_dir, basename)) as f:
        f.write(config)

def clear_efigrub(fqdn):
    """
    Removes bootloader file created by configure_efigrub
    """
    grub_dir = os.path.join(get_tftp_root(), 'grub')
    basename = pxe_basename(fqdn)
    logger.debug('Removing grub config for %s as %s', fqdn, basename)
    unlink_ignore(os.path.join(grub_dir, basename))


### Bootloader config: ZPXE (IBM zSeries)

def configure_zpxe(fqdn, kernel_options):
    """
    Creates bootloader files for ZPXE

    <get_tftp_root()>/s390x/s_<fqdn>
    <get_tftp_root()>/s390x/s_<fqdn>_parm
    <get_tftp_root()>/s390x/s_<fqdn>_conf
    """
    zpxe_dir = os.path.join(get_tftp_root(), 's390x')
    makedirs_ignore(zpxe_dir, mode=0755)

    kernel_options = "%s netboot_method=zpxe" % kernel_options
    # The structure of these files is dictated by zpxe.rexx,
    # Cobbler's "pseudo-PXE" for zVM on s390(x).
    # XXX I don't think multiple initrds are supported?
    logger.debug('Writing zpxe index file for %s', fqdn)
    with atomically_replaced_file(os.path.join(zpxe_dir, 's_%s' % fqdn)) as f:
        f.write('/images/%s/kernel\n/images/%s/initrd\n\n' % (fqdn, fqdn))
    logger.debug('Writing zpxe parm file for %s', fqdn)
    with atomically_replaced_file(os.path.join(zpxe_dir, 's_%s_parm' % fqdn)) as f:
        # must be wrapped at 80 columns
        rest = kernel_options
        while rest:
            f.write(rest[:80] + '\n')
            rest = rest[80:]
    logger.debug('Writing zpxe conf file for %s', fqdn)
    with atomically_replaced_file(os.path.join(zpxe_dir, 's_%s_conf' % fqdn)) as f:
        pass # unused, but zpxe.rexx fetches it anyway

def clear_zpxe(fqdn):
    """
    If this system is configured for zpxe, reconfigures for local boot

    Kept (set to 'local'): <get_tftp_root()>/s390x/s_<fqdn>
    Removed: <get_tftp_root()>/s390x/s_<fqdn>_parm
    Removed: <get_tftp_root()>/s390x/s_<fqdn>_conf
    """
    zpxe_dir = os.path.join(get_tftp_root(), 's390x')
    configname = os.path.join(zpxe_dir, 's_%s' % fqdn)
    if not os.path.exists(configname):
        # Don't create a default zpxe config if we didn't create
        # a zpxe config for this system
        return

    logger.debug('Writing "local" zpxe index file for %s', fqdn)
    with atomically_replaced_file(configname) as f:
        f.write('local\n') # XXX or should we just delete it??
    logger.debug('Removing zpxe parm file for %s', fqdn)
    unlink_ignore(os.path.join(zpxe_dir, 's_%s_parm' % fqdn))
    logger.debug('Removing zpxe conf file for %s', fqdn)
    unlink_ignore(os.path.join(zpxe_dir, 's_%s_conf' % fqdn))

### Bootloader config: EFI Linux (ELILO)

def configure_elilo(fqdn, kernel_options):
    """
    Creates bootloader file for ELILO

    <get_tftp_root()>/<pxe_basename(fqdn)>.conf
    """
    basename = '%s.conf' % pxe_basename(fqdn)
    # XXX I don't think multiple initrds are supported?
    config = '''relocatable

image=/images/%s/kernel
    label=netinstall
    append="%s netboot_method=elilo"
    initrd=/images/%s/initrd
    read-only
    root=/dev/ram
''' % (fqdn, kernel_options, fqdn)
    logger.debug('Writing elilo config for %s as %s', fqdn, basename)
    with atomically_replaced_file(os.path.join(get_tftp_root(), basename)) as f:
        f.write(config)

def clear_elilo(fqdn):
    """
    Removes bootloader file created by configure_elilo
    """
    basename = '%s.conf' % pxe_basename(fqdn)
    unlink_ignore(os.path.join(get_tftp_root(), basename))


### Bootloader config: PowerPC Open Firmware bootloader (Yaboot)

def configure_yaboot(fqdn, kernel_options):
    """
    Creates bootloader files for Yaboot

    <get_tftp_root()>/etc/<pxe_basename(fqdn).lower()>
    <get_tftp_root()>/ppc/<pxe_basename(fqdn).lower()> -> ../yaboot
    """
    yaboot_conf_dir = os.path.join(get_tftp_root(), 'etc')
    makedirs_ignore(yaboot_conf_dir, mode=0755)
    ppc_dir = os.path.join(get_tftp_root(), 'ppc')
    makedirs_ignore(ppc_dir, mode=0755)

    basename = pxe_basename(fqdn).lower()
    # XXX I don't think multiple initrds are supported?
    config = '''init-message="Beaker scheduled job for %s"
timeout=80
delay=10
default=linux

image=/images/%s/kernel
    label=linux
    initrd=/images/%s/initrd
    append="%s netboot_method=yaboot"
''' % (fqdn, fqdn, fqdn, kernel_options)
    logger.debug('Writing yaboot config for %s as %s', fqdn, basename)
    with atomically_replaced_file(os.path.join(yaboot_conf_dir, basename)) as f:
        f.write(config)
    logger.debug('Creating yaboot symlink for %s as %s', fqdn, basename)
    atomic_symlink('../yaboot', os.path.join(ppc_dir, basename))

def clear_yaboot(fqdn):
    """
    Removes bootloader file created by configure_yaboot
    """
    basename = pxe_basename(fqdn).lower()
    logger.debug('Removing yaboot config for %s as %s', fqdn, basename)
    unlink_ignore(os.path.join(get_tftp_root(), 'etc', basename))
    logger.debug('Removing yaboot symlink for %s as %s', fqdn, basename)
    unlink_ignore(os.path.join(get_tftp_root(), 'ppc', basename))


# Mass configuration

# We configure most known bootloaders for every system, in order
# to adjust automatically as existing bootloaders are ported to
# new architectures

# The sole exception is zxpe, as this leaves per-system config files
# in place after their "clear" operations in order to force the
# systems back into local booting mode. We restrict these to the
# relevant arches, so we don't end up with pointless filesystem
# clutter on the TFTP server.

class Bootloader(collections.namedtuple("Bootloader",
                                        "name configure clear arches")):
    def __repr__(self):
        return "Bootloader(%r)" % self.name

BOOTLOADERS = {}

def add_bootloader(name, configure, clear, arches=None):
    """Register bootloader configuration and clear functions"""
    if arches is None:
        arches = set()
    BOOTLOADERS[name] = Bootloader(name, configure, clear, arches)

add_bootloader("pxelinux", configure_pxelinux, clear_pxelinux)
add_bootloader("efigrub", configure_efigrub, clear_efigrub)
add_bootloader("yaboot", configure_yaboot, clear_yaboot)
add_bootloader("elilo", configure_elilo, clear_elilo)
add_bootloader("armlinux", configure_armlinux, clear_armlinux)
add_bootloader("aarch64", configure_aarch64, clear_aarch64, set(["aarch64"]))
add_bootloader("zpxe", configure_zpxe, clear_zpxe, set(["s390", "s390x"]))

def configure_all(fqdn, arch, distro_tree_id,
                  kernel_url, initrd_url, kernel_options):
    """Configure images and all bootloader files for given fqdn"""
    fetch_images(distro_tree_id, kernel_url, initrd_url, fqdn)
    arches = set(arch)
    for bootloader in BOOTLOADERS.values():
        if bootloader.arches and not (bootloader.arches & arches):
            # Arch constrained bootloader and this system doesn't match
            continue
        bootloader.configure(fqdn, kernel_options)

def clear_all(fqdn):
    """Clear images and all bootloader files for given fqdn"""
    clear_images(fqdn)
    for bootloader in BOOTLOADERS.values():
        bootloader.clear(fqdn)
