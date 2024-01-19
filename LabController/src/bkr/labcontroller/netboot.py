# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import collections
import errno
import logging
import os
import os.path
import shutil
import socket

import six
from six.moves import cStringIO as StringIO
from six.moves import urllib

from bkr.common.helpers import (
    atomic_link,
    atomic_symlink,
    atomically_replaced_file,
    makedirs_ignore,
    siphon,
    unlink_ignore,
)
from bkr.labcontroller.config import get_conf

logger = logging.getLogger(__name__)


class ImageFetchingError(Exception):
    """
    Raised when an error occurs while fetching netboot images from the network.
    """

    def __init__(self, url, distro_tree_id, cause):
        super(ImageFetchingError, self).__init__(
            "Error fetching image %s for distro tree %s: %s"
            % (url, distro_tree_id, cause)
        )


def get_tftp_root():
    return get_conf().get("TFTP_ROOT", "/var/lib/tftpboot")


def copy_ignore(path, source_file):
    """
    Creates and populates a file by copying from a source file object.
    The destination file will remain untouched if it already exists.
    """
    mode = "x" if six.PY3 else "wx"
    try:
        f = open(path, mode)
    except IOError as e:
        if e.errno == errno.EEXIST:
            return
        else:
            raise

    try:
        logger.debug("%s didn't exist, writing it", path)
        siphon(source_file, f)
    finally:
        f.close()


def write_ignore(path, content):
    """
    Creates and populates a file with the given string content.
    The destination file will remain untouched if it already exists.
    """
    copy_ignore(path, StringIO(content))


def copy_path_ignore(dest_path, source_path):
    """
    Creates and populates a file by copying from a source file.
    The destination file will remain untouched if it already exists.
    Nothing will be copied if the source file does not exist.
    """
    try:
        source_file = open(source_path, "rb")
    except IOError as e:
        if e.errno == errno.ENOENT:
            return
        else:
            raise
    try:
        copy_ignore(dest_path, source_file)
    finally:
        source_file.close()


def copy_default_loader_images():
    """
    Populates default boot loader images, where possible.

    Ultimately it is up to the administrator to make sure that their desired
    boot loader images are available and match their DHCP configuration.
    However we can copy in some common loader images to their default locations
    as a convenience.
    """
    # We could also copy EFI GRUB, on RHEL6 it's located at /boot/efi/EFI/redhat/grub.efi
    # ... the problem is that is either the ia32 version or the x64 version
    # depending on the architecture of the server, blerg.
    makedirs_ignore(get_tftp_root(), mode=0o755)
    copy_path_ignore(
        os.path.join(get_tftp_root(), "pxelinux.0"), "/usr/share/syslinux/pxelinux.0"
    )
    copy_path_ignore(
        os.path.join(get_tftp_root(), "menu.c32"), "/usr/share/syslinux/menu.c32"
    )


def fetch_bootloader_image(fqdn, fqdn_dir, distro_tree_id, image_url):
    timeout = get_conf().get("IMAGE_FETCH_TIMEOUT")
    logger.debug("Fetching bootloader image %s for %s", image_url, fqdn)
    with atomically_replaced_file(os.path.join(fqdn_dir, "image")) as dest:
        try:
            siphon(urllib.request.urlopen(image_url, timeout=timeout), dest)
        except Exception as e:
            raise ImageFetchingError(image_url, distro_tree_id, e)


def fetch_images(distro_tree_id, kernel_url, initrd_url, fqdn):
    """
    Creates references to kernel and initrd files at:

    <get_tftp_root()>/images/<fqdn>/kernel
    <get_tftp_root()>/images/<fqdn>/initrd
    """
    images_dir = os.path.join(get_tftp_root(), "images", fqdn)
    makedirs_ignore(images_dir, 0o755)
    # Only look for fetched images if distro_tree is registered
    if distro_tree_id is not None:
        distrotree_dir = os.path.join(
            get_tftp_root(), "distrotrees", str(distro_tree_id)
        )

        # beaker-pxemenu might have already fetched the images, so let's try there
        # before anywhere else.
        try:
            atomic_link(
                os.path.join(distrotree_dir, "kernel"),
                os.path.join(images_dir, "kernel"),
            )
            atomic_link(
                os.path.join(distrotree_dir, "initrd"),
                os.path.join(images_dir, "initrd"),
            )
            logger.debug(
                "Using images from distro tree %s for %s", distro_tree_id, fqdn
            )
            return
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        # No luck there, so try something else...

    timeout = get_conf().get("IMAGE_FETCH_TIMEOUT")
    logger.debug("Fetching kernel %s for %s", kernel_url, fqdn)
    with atomically_replaced_file(os.path.join(images_dir, "kernel")) as dest:
        try:
            siphon(urllib.request.urlopen(kernel_url, timeout=timeout), dest)
        except Exception as e:
            raise ImageFetchingError(kernel_url, distro_tree_id, e)
    logger.debug("Fetching initrd %s for %s", initrd_url, fqdn)
    with atomically_replaced_file(os.path.join(images_dir, "initrd")) as dest:
        try:
            siphon(urllib.request.urlopen(initrd_url, timeout=timeout), dest)
        except Exception as e:
            raise ImageFetchingError(initrd_url, distro_tree_id, e)


def have_images(fqdn):
    return os.path.exists(os.path.join(get_tftp_root(), "images", fqdn))


def clear_images(fqdn):
    """Removes kernel and initrd images"""
    images_dir = os.path.join(get_tftp_root(), "images", fqdn)
    logger.debug("Removing images for %s", fqdn)
    shutil.rmtree(images_dir, ignore_errors=True)


def pxe_basename(fqdn):
    # pxelinux uses upper-case hex IP address for config filename
    ipaddr = socket.gethostbyname(fqdn)
    return "%02X%02X%02X%02X" % tuple(int(octet) for octet in ipaddr.split("."))


def extract_arg(arg, kernel_options):
    """
    Returns a tuple of (<arg> value, rest of kernel options). If there was
    no <arg>, the result will be (None, untouched kernel options).
    """
    value = None
    tokens = []
    for token in kernel_options.split():
        if token.startswith(arg):
            value = token[len(arg) :]
        else:
            tokens.append(token)
    if value:
        return (value, " ".join(tokens))
    else:
        return (None, kernel_options)


def configure_grub2(
    fqdn, default_config_loc, config_file, kernel_options, devicetree=""
):
    grub2_postfix, kernel_options = extract_arg("grub2_postfix=", kernel_options)
    config = """\
linux%s  /images/%s/kernel %s netboot_method=grub2
initrd%s /images/%s/initrd
%s
boot
""" % (
        grub2_postfix or "",
        fqdn,
        kernel_options,
        grub2_postfix or "",
        fqdn,
        devicetree,
    )
    with atomically_replaced_file(config_file) as f:
        f.write(config)
    # We also ensure a default config exists that exits
    write_ignore(os.path.join(default_config_loc, "grub.cfg"), "exit\n")


def clear_grub2(config):
    unlink_ignore(config)


# Bootloader config: PXE Linux for aarch64
def configure_aarch64(fqdn, kernel_options, basedir):
    """
    Creates PXE bootloader files for aarch64 Linux

    <get_tftp_root()>/aarch64/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/EFI/BOOT/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/EFI/BOOT/grub.cfg
    """
    grub2_conf = "grub.cfg-%s" % pxe_basename(fqdn)
    pxe_base = os.path.join(basedir, "aarch64")
    makedirs_ignore(pxe_base, mode=0o755)

    efi_conf_dir = os.path.join(basedir, "EFI", "BOOT")
    makedirs_ignore(efi_conf_dir, mode=0o755)

    devicetree, kernel_options = extract_arg("devicetree=", kernel_options)
    if devicetree:
        devicetree = "devicetree %s" % devicetree
    else:
        devicetree = ""

    grub_cfg_file = os.path.join(efi_conf_dir, grub2_conf)
    logger.debug("Writing aarch64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, efi_conf_dir, grub_cfg_file, kernel_options, devicetree)

    grub_cfg_file = os.path.join(pxe_base, grub2_conf)
    logger.debug("Writing aarch64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, pxe_base, grub_cfg_file, kernel_options, devicetree)


def clear_aarch64(fqdn, basedir):
    """
    Removes PXE bootloader file created by configure_aarch64
    """
    pxe_base = os.path.join(basedir, "aarch64")
    basename = "grub.cfg-%s" % pxe_basename(fqdn)
    logger.debug("Removing aarch64 config for %s as %s", fqdn, basename)
    clear_grub2(os.path.join(pxe_base, basename))


# Bootloader config: PXE Linux for ARM
def configure_armlinux(fqdn, kernel_options, basedir):
    """
    Creates PXE bootloader files for ARM Linux

    <get_tftp_root()>/arm/pxelinux.cfg/<pxe_basename(fqdn)>

    Also ensures empty config file exists:

    <get_tftp_root()>/arm/empty

    Specify filename "arm/empty"; in your dhcpd.conf file
    This is needed to set a path prefix of arm so that we don't
    conflict with x86 pxelinux.cfg files.
    """
    pxe_base = os.path.join(basedir, "arm")
    makedirs_ignore(pxe_base, mode=0o755)
    write_ignore(os.path.join(pxe_base, "empty"), "")
    pxe_dir = os.path.join(pxe_base, "pxelinux.cfg")
    makedirs_ignore(pxe_dir, mode=0o755)

    basename = pxe_basename(fqdn)
    config = """default linux
prompt 0
timeout 100
label linux
    kernel ../images/%s/kernel
    initrd ../images/%s/initrd
    append %s netboot_method=armpxe
""" % (
        fqdn,
        fqdn,
        kernel_options,
    )
    logger.debug("Writing armlinux config for %s as %s", fqdn, basename)
    with atomically_replaced_file(os.path.join(pxe_dir, basename)) as f:
        f.write(config)


def clear_armlinux(fqdn, basedir):
    """
    Removes PXE bootloader file created by configure_armlinux
    """
    pxe_dir = os.path.join(basedir, "arm", "pxelinux.cfg")
    basename = pxe_basename(fqdn)
    logger.debug("Removing armlinux config for %s as %s", fqdn, basename)
    unlink_ignore(os.path.join(pxe_dir, basename))
    # XXX Should we save a default config, the way we do for non-ARM PXE?


def _configure_pxelinux_config(basedir, fqdn, initrd_defined, kernel_options, symlink):
    """
    Prepare configuration file for PXELINUX

    Kernel and initrd has to be relative to image location
    """
    kernel = os.path.join("images", fqdn, "kernel")
    initrd = os.path.join("images", fqdn, "initrd")

    path_diff = os.path.relpath(get_tftp_root(), basedir)
    kernel = os.path.join(path_diff if symlink else "/", kernel)
    initrd = os.path.join(path_diff if symlink else "/", initrd)

    # Unfortunately the initrd kernel arg needs some special handling. It can be
    # supplied from the Beaker side (e.g. a system-specific driver disk) but we
    # also supply the main initrd here which we have fetched from the distro.
    if initrd_defined:
        initrd = "{0},{1}".format(initrd, initrd_defined)

    return """default linux
prompt 0
timeout 100
label linux
    kernel %s
    ipappend 2
    append initrd=%s %s netboot_method=pxe
""" % (
        kernel,
        initrd,
        kernel_options,
    )


# Bootloader config: PXE Linux
def configure_pxelinux(fqdn, kernel_options, basedir, symlink=False):
    """
    Creates PXE bootloader files for PXE Linux

    <get_tftp_root()>/pxelinux.cfg/<pxe_basename(fqdn)>

    Also ensures default (localboot) config exists:

    <get_tftp_root()>/pxelinux.cfg/default
    """
    pxe_dir = os.path.join(basedir, "pxelinux.cfg")
    makedirs_ignore(pxe_dir, mode=0o755)

    basename = pxe_basename(fqdn)
    initrd, kernel_options = extract_arg("initrd=", kernel_options)

    config = _configure_pxelinux_config(basedir, fqdn, initrd, kernel_options, symlink)

    logger.debug("Writing pxelinux config for %s as %s", fqdn, basename)
    with atomically_replaced_file(os.path.join(pxe_dir, basename)) as f:
        f.write(config)
    # We also ensure a default config exists that falls back to local boot
    write_ignore(
        os.path.join(pxe_dir, "default"),
        """default local
prompt 0
timeout 0
label local
    localboot 0
""",
    )


def clear_pxelinux(fqdn, basedir):
    """
    Removes PXE bootloader file created by configure_pxelinux
    """
    pxe_dir = os.path.join(basedir, "pxelinux.cfg")
    basename = pxe_basename(fqdn)
    configname = os.path.join(pxe_dir, basename)
    logger.debug("Removing pxelinux config for %s as %s", fqdn, basename)
    unlink_ignore(configname)


### Bootloader config: iPXE
def configure_ipxe(fqdn, kernel_options, basedir):
    """
    Creates iPXE bootloader files

    <get_tftp_root()>/ipxe/<pxe_basename(fqdn).lower()>

    Also ensures default (localboot) config exists:

    <get_tftp_root()>/ipxe/default
    """
    ipxe_dir = os.path.join(basedir, "ipxe")
    makedirs_ignore(ipxe_dir, mode=0o755)

    basename = pxe_basename(fqdn).lower()
    # Unfortunately the initrd kernel arg needs some special handling. It can be
    # supplied from the Beaker side (e.g. a system-specific driver disk) but we
    # also supply the main initrd here which we have fetched from the distro.
    initrd, kernel_options = extract_arg("initrd=", kernel_options)
    if initrd:
        initrd = "/images/%s/initrd\ninitrd %s" % (fqdn, initrd)
    else:
        initrd = "/images/%s/initrd" % fqdn
    config = """#!ipxe
kernel /images/%s/kernel
initrd %s
imgargs kernel initrd=initrd %s netboot_method=ipxe BOOTIF=01-${netX/mac:hexhyp}
boot || exit 1
""" % (
        fqdn,
        initrd,
        kernel_options,
    )
    logger.debug("Writing ipxe config for %s as %s", fqdn, basename)
    with atomically_replaced_file(os.path.join(ipxe_dir, basename)) as f:
        f.write(config)
    # We also ensure a default config exists that falls back to local boot
    write_ignore(
        os.path.join(ipxe_dir, "default"),
        """#!ipxe
iseq ${builtin/platform} pcbios && sanboot --no-describe --drive 0x80 ||
exit 1
""",
    )


def clear_ipxe(fqdn, basedir):
    """
    Removes iPXE bootloader file created by configure_ipxe
    """
    ipxe_dir = os.path.join(basedir, "ipxe")
    basename = pxe_basename(fqdn).lower()
    configname = os.path.join(ipxe_dir, basename)
    logger.debug("Removing iPXE config for %s as %s", fqdn, basename)
    unlink_ignore(configname)


### Bootloader config: EFI GRUB
def configure_efigrub(fqdn, kernel_options, basedir):
    """
    Creates bootloader file for EFI GRUB

    <get_tftp_root()>/grub/<pxe_basename(fqdn)>

    Also ensures images symlink exists:

    <get_tftp_root()>/grub/images -> <get_tftp_root()>/images
    """
    grub_dir = os.path.join(basedir, "grub")
    makedirs_ignore(grub_dir, mode=0o755)
    atomic_symlink("../images", os.path.join(grub_dir, "images"))

    basename = pxe_basename(fqdn)
    # Unfortunately the initrd kernel arg needs some special handling. It can be
    # supplied from the Beaker side (e.g. a system-specific driver disk) but we
    # also supply the main initrd here which we have fetched from the distro.
    initrd, kernel_options = extract_arg("initrd=", kernel_options)
    if initrd:
        initrd = " ".join(["/images/%s/initrd" % fqdn] + initrd.split(","))
    else:
        initrd = "/images/%s/initrd" % fqdn
    config = """default 0
timeout 10
title Beaker scheduled job for %s
    root (nd)
    kernel /images/%s/kernel %s netboot_method=efigrub
    initrd %s
""" % (
        fqdn,
        fqdn,
        kernel_options,
        initrd,
    )
    logger.debug("Writing grub config for %s as %s", fqdn, basename)
    with atomically_replaced_file(os.path.join(grub_dir, basename)) as f:
        f.write(config)


def clear_efigrub(fqdn, basedir):
    """
    Removes bootloader file created by configure_efigrub
    """
    grub_dir = os.path.join(basedir, "grub")
    basename = pxe_basename(fqdn)
    logger.debug("Removing grub config for %s as %s", fqdn, basename)
    unlink_ignore(os.path.join(grub_dir, basename))


# Bootloader config: ZPXE (IBM zSeries)
def configure_zpxe(fqdn, kernel_url, initrd_url, kernel_options, basedir):
    """
    Creates bootloader files for ZPXE

    <get_tftp_root()>/s390x/s_<fqdn>
    <get_tftp_root()>/s390x/s_<fqdn>_parm
    <get_tftp_root()>/s390x/s_<fqdn>_conf
    """
    zpxe_dir = os.path.join(basedir, "s390x")
    makedirs_ignore(zpxe_dir, mode=0o755)

    kernel_options = "%s netboot_method=zpxe" % kernel_options
    # The structure of these files is dictated by zpxe.rexx,
    # Cobbler's "pseudo-PXE" for zVM on s390(x).
    # XXX I don't think multiple initrds are supported?
    logger.debug("Writing zpxe index file for %s", fqdn)
    with atomically_replaced_file(os.path.join(zpxe_dir, "s_%s" % fqdn)) as f:
        if get_conf().get("ZPXE_USE_FTP", True):
            if not kernel_url.startswith("ftp://") or not initrd_url.startswith(
                "ftp://"
            ):
                raise ValueError("zPXE only supports FTP for downloading images")
            f.write("%s\n%s\n\n" % (kernel_url, initrd_url))
        else:
            f.write("/images/%s/kernel\n/images/%s/initrd\n\n" % (fqdn, fqdn))
    logger.debug("Writing zpxe parm file for %s", fqdn)
    with atomically_replaced_file(os.path.join(zpxe_dir, "s_%s_parm" % fqdn)) as f:
        # must be wrapped at 80 columns
        rest = kernel_options
        while rest:
            f.write(rest[:80] + "\n")
            rest = rest[80:]
    logger.debug("Writing zpxe conf file for %s", fqdn)
    with atomically_replaced_file(os.path.join(zpxe_dir, "s_%s_conf" % fqdn)) as f:
        pass  # unused, but zpxe.rexx fetches it anyway


def clear_zpxe(fqdn, basedir):
    """
    If this system is configured for zpxe, reconfigures for local boot

    Kept (set to 'local'): <get_tftp_root()>/s390x/s_<fqdn>
    Removed: <get_tftp_root()>/s390x/s_<fqdn>_parm
    Removed: <get_tftp_root()>/s390x/s_<fqdn>_conf
    """
    zpxe_dir = os.path.join(basedir, "s390x")
    configname = os.path.join(zpxe_dir, "s_%s" % fqdn)
    if not os.path.exists(configname):
        # Don't create a default zpxe config if we didn't create
        # a zpxe config for this system
        return

    logger.debug('Writing "local" zpxe index file for %s', fqdn)
    with atomically_replaced_file(configname) as f:
        f.write("local\n")  # XXX or should we just delete it??
    logger.debug("Removing zpxe parm file for %s", fqdn)
    unlink_ignore(os.path.join(zpxe_dir, "s_%s_parm" % fqdn))
    logger.debug("Removing zpxe conf file for %s", fqdn)
    unlink_ignore(os.path.join(zpxe_dir, "s_%s_conf" % fqdn))


# Bootloader config: EFI Linux (ELILO)
def configure_elilo(fqdn, kernel_options, basedir):
    """
    Creates bootloader file for ELILO

    <get_tftp_root()>/<pxe_basename(fqdn)>.conf
    """
    basename = "%s.conf" % pxe_basename(fqdn)
    # XXX I don't think multiple initrds are supported?
    config = """relocatable

image=/images/%s/kernel
    label=netinstall
    append="%s netboot_method=elilo"
    initrd=/images/%s/initrd
    read-only
    root=/dev/ram
""" % (
        fqdn,
        kernel_options,
        fqdn,
    )
    logger.debug("Writing elilo config for %s as %s", fqdn, basename)
    with atomically_replaced_file(os.path.join(basedir, basename)) as f:
        f.write(config)


def clear_elilo(fqdn, basedir):
    """
    Removes bootloader file created by configure_elilo
    """
    basename = "%s.conf" % pxe_basename(fqdn)
    unlink_ignore(os.path.join(basedir, basename))


# Bootloader config: PowerPC Open Firmware bootloader (Yaboot)
def configure_yaboot(fqdn, kernel_options, basedir, yaboot_symlink=True):
    """
    Creates bootloader files for Yaboot

    <get_tftp_root()>/etc/<pxe_basename(fqdn).lower()>
    <get_tftp_root()>/ppc/<pxe_basename(fqdn).lower()> -> ../yaboot
    """
    yaboot_conf_dir = os.path.join(basedir, "etc")
    makedirs_ignore(yaboot_conf_dir, mode=0o755)

    basename = pxe_basename(fqdn).lower()
    # XXX I don't think multiple initrds are supported?
    config = """init-message="Beaker scheduled job for %s"
timeout=80
delay=10
default=linux

image=/images/%s/kernel
    label=linux
    initrd=/images/%s/initrd
    append="%s netboot_method=yaboot"
""" % (
        fqdn,
        fqdn,
        fqdn,
        kernel_options,
    )
    logger.debug("Writing yaboot config for %s as %s", fqdn, basename)
    with atomically_replaced_file(os.path.join(yaboot_conf_dir, basename)) as f:
        f.write(config)
    if yaboot_symlink:
        ppc_dir = os.path.join(basedir, "ppc")
        makedirs_ignore(ppc_dir, mode=0o755)
        logger.debug("Creating yaboot symlink for %s as %s", fqdn, basename)
        atomic_symlink("../yaboot", os.path.join(ppc_dir, basename))


def clear_yaboot(fqdn, basedir, yaboot_symlink=True):
    """
    Removes bootloader file created by configure_yaboot
    """
    basename = pxe_basename(fqdn).lower()
    logger.debug("Removing yaboot config for %s as %s", fqdn, basename)
    unlink_ignore(os.path.join(basedir, "etc", basename))
    if yaboot_symlink:
        logger.debug("Removing yaboot symlink for %s as %s", fqdn, basename)
        unlink_ignore(os.path.join(basedir, "ppc", basename))


# Bootloader config for X86_64
def configure_x86_64(fqdn, kernel_options, basedir):
    """
    Calls configure_grub2() to create the machine config files to GRUB2
    boot loader.

    <get_tftp_root()>/EFI/BOOT/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/EFI/BOOT/grub.cfg
    <get_tftp_root()>/x86_64/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/x86_64/grub.cfg
    <get_tftp_root()>/boot/grub2/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/boot/grub2/grub.cfg
    """

    grub2_conf = "grub.cfg-%s" % pxe_basename(fqdn)

    efi_conf_dir = os.path.join(basedir, "EFI", "BOOT")
    makedirs_ignore(efi_conf_dir, mode=0o755)
    grub_cfg_file = os.path.join(efi_conf_dir, grub2_conf)
    logger.debug("Writing grub2/x86_64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, efi_conf_dir, grub_cfg_file, kernel_options)

    x86_64_dir = os.path.join(basedir, "x86_64")
    makedirs_ignore(x86_64_dir, mode=0o755)
    grub_cfg_file = os.path.join(x86_64_dir, grub2_conf)
    logger.debug("Writing grub2/x86_64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, x86_64_dir, grub_cfg_file, kernel_options)

    # Location can be used as fallback
    # Mostly old GRUB2 relying on this location
    grub2_conf_dir = os.path.join(basedir, "boot", "grub2")
    makedirs_ignore(grub2_conf_dir, mode=0o755)
    grub_cfg_file = os.path.join(grub2_conf_dir, grub2_conf)
    logger.debug("Writing grub2/x86_64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, grub2_conf_dir, grub_cfg_file, kernel_options)


def clear_x86_64(fqdn, basedir):
    """
    Calls clear_grub2() to remove the machine config file and symlink to
    the grub2 boot loader
    """
    x86_64_dir = os.path.join(basedir, "x86_64")
    grub2_config = "grub.cfg-%s" % pxe_basename(fqdn)

    logger.debug("Removing grub2/x86_64 config for %s as %s", fqdn, grub2_config)
    clear_grub2(os.path.join(x86_64_dir, grub2_config))

    grub2_conf_dir = os.path.join(basedir, "boot", "grub2")

    logger.debug("Removing grub2/x86_64 config for %s as %s", fqdn, grub2_config)
    clear_grub2(os.path.join(grub2_conf_dir, grub2_config))


# Bootloader config for PPC64
def configure_ppc64(fqdn, kernel_options, basedir):
    """
    Calls configure_grub2() to create the machine config files and symlink
    to the grub2 boot loader:

    <get_tftp_root()>/ppc/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/ppc/grub.cfg
    <get_tftp_root()>/ppc/<pxe_basename(fqdn).lower()-grub2> -> ../boot/grub2/powerpc-ieee1275/core.elf

    # Hacks, see the note below
    <get_tftp_root()>/grub.cfg-<pxe_basename(fqdn)>
    <get_tftp_root()>/boot/grub2/grub.cfg-<pxe_basename(fqdn)>


    """
    ppc_dir = os.path.join(basedir, "ppc")
    makedirs_ignore(ppc_dir, mode=0o755)

    grub_cfg_file = os.path.join(ppc_dir, "grub.cfg-%s" % pxe_basename(fqdn))
    logger.debug("Writing grub2/ppc64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, ppc_dir, grub_cfg_file, kernel_options)

    # The following two hacks are to accommodate the differences in behavior
    # among various power configurations and grub2 versions
    # Remove them once they are sorted out (also see the relevant
    # code in clear_ppc64())
    # Ref: https://bugzilla.redhat.com/show_bug.cgi?id=1144106

    # hack for older grub
    grub2_conf_dir = os.path.join(basedir, "boot", "grub2")
    makedirs_ignore(grub2_conf_dir, mode=0o755)
    grub_cfg_file = os.path.join(grub2_conf_dir, "grub.cfg-%s" % pxe_basename(fqdn))
    logger.debug("Writing grub2/ppc64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, grub2_conf_dir, grub_cfg_file, kernel_options)

    # hack for power VMs
    grub_cfg_file = os.path.join(basedir, "grub.cfg-%s" % pxe_basename(fqdn))
    logger.debug("Writing grub2/ppc64 config for %s as %s", fqdn, grub_cfg_file)
    configure_grub2(fqdn, ppc_dir, grub_cfg_file, kernel_options)

    grub2_symlink = "%s-grub2" % pxe_basename(fqdn).lower()
    logger.debug("Creating grub2 symlink for %s as %s", fqdn, grub2_symlink)
    atomic_symlink(
        "../boot/grub2/powerpc-ieee1275/core.elf", os.path.join(ppc_dir, grub2_symlink)
    )


def clear_ppc64(fqdn, basedir):
    """
    Calls clear_grub2() to remove the machine config file and symlink to
    the grub2 boot loader
    """
    ppc_dir = os.path.join(basedir, "ppc")
    grub2_config = "grub.cfg-%s" % pxe_basename(fqdn)
    logger.debug("Removing grub2/ppc64 config for %s as %s", fqdn, grub2_config)
    clear_grub2(os.path.join(ppc_dir, grub2_config))
    grub2_symlink = "%s-grub2" % pxe_basename(fqdn).lower()
    logger.debug("Removing grub2 symlink for %s as %s", fqdn, grub2_symlink)
    clear_grub2(os.path.join(ppc_dir, grub2_symlink))

    # clear the files which were created as a result of the hacks
    # mentioned in configure_ppc64()
    grub2_conf_dir = os.path.join(basedir, "boot", "grub2")
    grub2_config = "grub.cfg-%s" % pxe_basename(fqdn)
    logger.debug("Removing grub2/ppc64 config for %s as %s", fqdn, grub2_config)
    clear_grub2(os.path.join(grub2_conf_dir, grub2_config))
    grub2_config = "grub.cfg-%s" % pxe_basename(fqdn)
    logger.debug("Removing grub2/ppc64 config for %s as %s", fqdn, grub2_config)
    clear_grub2(os.path.join(basedir, grub2_config))


def configure_petitboot(fqdn, ko, basedir):
    """
    Creates bootloader file for petitboot

    basedir/bootloader/<fqdn>/petitboot.cfg
    """
    config = """default Beaker scheduled job for %s
label Beaker scheduled job for %s
kernel ::/images/%s/kernel
initrd ::/images/%s/initrd
append %s netboot_method=petitboot
""" % (
        fqdn,
        fqdn,
        fqdn,
        fqdn,
        ko,
    )

    if not basedir:
        basedir = get_tftp_root()
    petitboot_conf_dir = os.path.join(basedir, "bootloader", fqdn)
    makedirs_ignore(petitboot_conf_dir, mode=0o755)
    logger.debug(
        "Writing petitboot config for %s as %s",
        fqdn,
        os.path.join(petitboot_conf_dir, "petitboot.cfg"),
    )
    with atomically_replaced_file(
        os.path.join(petitboot_conf_dir, "petitboot.cfg")
    ) as f:
        f.write(config)


def clear_petitboot(fqdn, basedir):
    """
    Removes bootloader file created by configure_petitboot
    """
    if not basedir:
        basedir = get_tftp_root()
    petitboot_conf_dir = os.path.join(basedir, "bootloader", fqdn)
    unlink_ignore(os.path.join(petitboot_conf_dir, "petitboot.cfg"))


# Mass configuration

# We configure most known bootloaders for every system, in order
# to adjust automatically as existing bootloaders are ported to
# new architectures

# The sole exception is zxpe, as this leaves per-system config files
# in place after their "clear" operations in order to force the
# systems back into local booting mode. We restrict these to the
# relevant arches, so we don't end up with pointless filesystem
# clutter on the TFTP server.


class Bootloader(collections.namedtuple("Bootloader", "name configure clear arches")):
    def __repr__(self):
        return "Bootloader(%r)" % self.name


BOOTLOADERS = {}


def add_bootloader(name, configure, clear, arches=None):
    """Register bootloader configuration and clear functions"""
    if arches is None:
        arches = set()
    BOOTLOADERS[name] = Bootloader(name, configure, clear, arches)


add_bootloader("pxelinux", configure_pxelinux, clear_pxelinux)
add_bootloader("ipxe", configure_ipxe, clear_ipxe)
add_bootloader("efigrub", configure_efigrub, clear_efigrub)
add_bootloader("yaboot", configure_yaboot, clear_yaboot)
add_bootloader("grub2", configure_ppc64, clear_ppc64, set(["ppc64", "ppc64le"]))
add_bootloader("grub2_x86_64", configure_x86_64, clear_x86_64, set(["x86_64"]))
add_bootloader("elilo", configure_elilo, clear_elilo)
add_bootloader("armlinux", configure_armlinux, clear_armlinux)
add_bootloader("aarch64", configure_aarch64, clear_aarch64, set(["aarch64"]))
# configure_zpxe and clear_zpxe are called explicitly because their arguments differ
add_bootloader("petitboot", configure_petitboot, clear_petitboot)


# Custom bootloader stuff
def configure_netbootloader_directory(fqdn, fqdn_dir, kernel_options):
    logger.debug("Creating custom netbootloader tree for %s in %s", fqdn, fqdn_dir)
    makedirs_ignore(fqdn_dir, mode=0o755)
    grub2_cfg_file = os.path.join(fqdn_dir, "grub.cfg-%s" % pxe_basename(fqdn))
    configure_grub2(fqdn, fqdn_dir, grub2_cfg_file, kernel_options)
    configure_pxelinux(fqdn, kernel_options, fqdn_dir, symlink=True)
    configure_ipxe(fqdn, kernel_options, fqdn_dir)
    configure_yaboot(fqdn, kernel_options, fqdn_dir, yaboot_symlink=False)


def clear_netbootloader_directory(fqdn):
    fqdn_dir = os.path.join(get_tftp_root(), "bootloader", fqdn)
    logger.debug("Removing custom netbootloader config for %s from %s", fqdn, fqdn_dir)
    unlink_ignore(os.path.join(fqdn_dir, "image"))
    grub2_cfg_file = os.path.join(fqdn_dir, "grub.cfg-%s" % pxe_basename(fqdn))
    clear_grub2(grub2_cfg_file)
    clear_pxelinux(fqdn, fqdn_dir)
    clear_ipxe(fqdn, fqdn_dir)
    clear_yaboot(fqdn, fqdn_dir, yaboot_symlink=False)


def configure_all(
    fqdn,
    arch,
    distro_tree_id,
    kernel_url,
    initrd_url,
    kernel_options,
    image_url,
    basedir=None,
):
    """Configure images and all bootloader files for given fqdn"""
    fetch_images(distro_tree_id, kernel_url, initrd_url, fqdn)
    if not basedir:
        basedir = get_tftp_root()
    netbootloader, kernel_options = extract_arg("netbootloader=", kernel_options)
    for bootloader in BOOTLOADERS.values():
        if bootloader.arches and arch not in bootloader.arches:
            # Arch constrained bootloader and this system doesn't match
            continue
        bootloader.configure(fqdn, kernel_options, basedir)
    if arch == "s390" or arch == "s390x":
        configure_zpxe(fqdn, kernel_url, initrd_url, kernel_options, basedir)

    # Custom boot loader code
    tftp_root = get_tftp_root()
    fqdn_dir = os.path.join(tftp_root, "bootloader", fqdn)

    if image_url or netbootloader:
        configure_netbootloader_directory(fqdn, fqdn_dir, kernel_options)

        if image_url:
            fetch_bootloader_image(fqdn, fqdn_dir, distro_tree_id, image_url)
        else:
            # create the symlink to the specified bootloader w.r.t the tftp_root
            if netbootloader.startswith("/"):
                netbootloader = netbootloader.lstrip("/")
            atomic_symlink(
                os.path.join("../../", netbootloader), os.path.join(fqdn_dir, "image")
            )


def clear_all(fqdn, basedir=None):
    """Clear images and all bootloader files for given fqdn"""
    clear_images(fqdn)
    if not basedir:
        basedir = get_tftp_root()
    for bootloader in BOOTLOADERS.values():
        bootloader.clear(fqdn, basedir)
    clear_zpxe(fqdn, basedir)
    clear_netbootloader_directory(fqdn)
