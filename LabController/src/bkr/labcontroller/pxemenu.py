# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import errno
import os
import os.path
import re
import shutil
import sys
from optparse import OptionParser

from jinja2 import Environment, PackageLoader
from six.moves import urllib, xmlrpc_client

from bkr.common.helpers import (
    atomic_symlink,
    atomically_replaced_file,
    makedirs_ignore,
    siphon,
)
from bkr.labcontroller.config import get_conf


def _get_url(available):
    for lc, url in available:
        # We prefer http
        if url.startswith("http:") or url.startswith("https:"):
            return url
    for lc, url in available:
        if url.startswith("ftp:"):
            return url
    raise ValueError(
        "Unrecognised URL scheme found in distro tree URL(s) %s"
        % [url for lc, url in available]
    )


def _group_distro_trees(distro_trees):
    grouped = {}
    for dt in distro_trees:
        grouped.setdefault(dt["distro_osmajor"], {}).setdefault(
            dt["distro_osversion"], []
        ).append(dt)
    return grouped


def _get_images(tftp_root, distro_tree_id, url, images):
    dest_dir = os.path.join(tftp_root, "distrotrees", str(distro_tree_id))
    makedirs_ignore(dest_dir, mode=0o755)
    for image_type, path in images:
        if image_type in ("kernel", "initrd"):
            dest_path = os.path.join(dest_dir, image_type)
            if os.path.isfile(dest_path):
                print(
                    "Skipping existing %s for distro tree %s"
                    % (image_type, distro_tree_id)
                )
            else:
                image_url = urllib.parse.urljoin(url, path)
                print(
                    "Fetching %s %s for distro tree %s"
                    % (image_type, image_url, distro_tree_id)
                )
                with atomically_replaced_file(dest_path) as dest:
                    siphon(urllib.request.urlopen(image_url), dest)


def _get_all_images(tftp_root, distro_trees):
    """
    Fetch all images for the given distro trees and return a new list of distro
    trees for which image can be fetched.
    """
    trees = []
    for distro_tree in distro_trees:
        url = _get_url(distro_tree["available"])
        try:
            _get_images(
                tftp_root, distro_tree["distro_tree_id"], url, distro_tree["images"]
            )
            trees.append(distro_tree)
        except IOError as e:
            sys.stderr.write(
                "Error fetching images for distro tree %s: %s\n"
                % (distro_tree["distro_tree_id"], e)
            )
    return trees


# configure Jinja2 to load menu templates
template_env = Environment(
    loader=PackageLoader("bkr.labcontroller", "pxemenu-templates"), trim_blocks=True
)
template_env.filters["get_url"] = _get_url


def write_menu(menu, template_name, distro_trees):
    osmajors = _group_distro_trees(distro_trees)
    with menu as menu:
        template = template_env.get_template(template_name)
        menu.write(template.render({"osmajors": osmajors}))


def write_menus(tftp_root, tags, xml_filter):
    conf = get_conf()

    # The order of steps for cleaning images is important,
    # to avoid races and to avoid deleting stuff we shouldn't:
    # first read the directory,
    # then fetch the list of trees,
    # and then remove any which aren't in the list.
    try:
        existing_tree_ids = os.listdir(os.path.join(tftp_root, "distrotrees"))
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        existing_tree_ids = []

    proxy = xmlrpc_client.ServerProxy("http://localhost:8000", allow_none=True)
    distro_trees = proxy.get_distro_trees(
        {
            "arch": ["x86_64", "i386", "aarch64", "ppc64", "ppc64le"],
            "tags": tags,
            "xml": xml_filter,
        }
    )
    current_tree_ids = set(str(dt["distro_tree_id"]) for dt in distro_trees)
    obsolete_tree_ids = set(existing_tree_ids).difference(current_tree_ids)
    print("Removing images for %s obsolete distro trees" % len(obsolete_tree_ids))
    for obs in obsolete_tree_ids:
        shutil.rmtree(os.path.join(tftp_root, "distrotrees", obs), ignore_errors=True)

    # Fetch images for all the distro trees first.
    print("Fetching images for all the distro trees")
    distro_trees = _get_all_images(tftp_root, distro_trees)

    x86_distrotrees = [
        distro for distro in distro_trees if distro["arch"] in ["x86_64", "i386"]
    ]
    print("Generating PXELINUX menus for %s distro trees" % len(x86_distrotrees))
    makedirs_ignore(os.path.join(tftp_root, "pxelinux.cfg"), mode=0o755)
    pxe_menu = atomically_replaced_file(
        os.path.join(tftp_root, "pxelinux.cfg", "beaker_menu")
    )
    write_menu(pxe_menu, "pxelinux-menu", x86_distrotrees)

    ipxe_distrotrees = [
        distro
        for distro in distro_trees
        if distro["arch"] in ["x86_64", "i386", "aarch64"]
    ]
    print("Generating iPXE menus for %s distro trees" % len(ipxe_distrotrees))
    makedirs_ignore(os.path.join(tftp_root, "ipxe"), mode=0o755)
    pxe_menu = atomically_replaced_file(os.path.join(tftp_root, "ipxe", "beaker_menu"))
    write_menu(pxe_menu, "ipxe-menu", ipxe_distrotrees)

    x86_efi_distrotrees = [
        distro for distro in distro_trees if distro["arch"] == "x86_64"
    ]
    # Regardless of any filtering options selected by the admin, we always
    # filter out certain distros which are known not to have EFI support. This
    # is a space saving measure for the EFI GRUB menu, which can't be nested so
    # we try to keep it as small possible.
    x86_efi_distrotrees = [
        distro
        for distro in x86_efi_distrotrees
        if not re.match(conf["EFI_EXCLUDED_OSMAJORS_REGEX"], distro["distro_osmajor"])
    ]

    print("Generating EFI GRUB menus for %s distro trees" % len(x86_efi_distrotrees))
    makedirs_ignore(os.path.join(tftp_root, "grub"), mode=0o755)
    atomic_symlink("../distrotrees", os.path.join(tftp_root, "grub", "distrotrees"))
    efi_grub_menu = atomically_replaced_file(
        os.path.join(tftp_root, "grub", "efidefault")
    )
    write_menu(efi_grub_menu, "efi-grub-menu", x86_efi_distrotrees)

    print(
        "Generating GRUB2 menus for x86 EFI for %s distro trees"
        % len(x86_efi_distrotrees)
    )
    makedirs_ignore(os.path.join(tftp_root, "boot", "grub2"), mode=0o755)
    x86_grub2_menu = atomically_replaced_file(
        os.path.join(tftp_root, "boot", "grub2", "beaker_menu_x86.cfg")
    )
    write_menu(x86_grub2_menu, "grub2-menu", x86_efi_distrotrees)

    ppc64_distrotrees = [distro for distro in distro_trees if distro["arch"] == "ppc64"]
    if ppc64_distrotrees:
        print(
            "Generating GRUB2 menus for PPC64 EFI for %s distro trees"
            % len(ppc64_distrotrees)
        )
        makedirs_ignore(os.path.join(tftp_root, "boot", "grub2"), mode=0o755)
        ppc64_grub2_menu = atomically_replaced_file(
            os.path.join(tftp_root, "boot", "grub2", "beaker_menu_ppc64.cfg")
        )
        write_menu(ppc64_grub2_menu, "grub2-menu", ppc64_distrotrees)

    ppc64le_distrotrees = [
        distro for distro in distro_trees if distro["arch"] == "ppc64le"
    ]
    if ppc64le_distrotrees:
        print(
            "Generating GRUB2 menus for PPC64LE EFI for %s distro trees"
            % len(ppc64_distrotrees)
        )
        makedirs_ignore(os.path.join(tftp_root, "boot", "grub2"), mode=0o755)
        ppc64le_grub2_menu = atomically_replaced_file(
            os.path.join(tftp_root, "boot", "grub2", "beaker_menu_ppc64le.cfg")
        )
        write_menu(ppc64le_grub2_menu, "grub2-menu", ppc64le_distrotrees)

    # XXX: would be nice if we can find a good time to move this into boot/grub2
    aarch64_distrotrees = [
        distro for distro in distro_trees if distro["arch"] == "aarch64"
    ]
    if aarch64_distrotrees:
        print(
            "Generating GRUB2 menus for aarch64 for %s distro trees"
            % len(aarch64_distrotrees)
        )
        makedirs_ignore(os.path.join(tftp_root, "aarch64"), mode=0o755)
        aarch64_menu = atomically_replaced_file(
            os.path.join(tftp_root, "aarch64", "beaker_menu.cfg")
        )
        write_menu(aarch64_menu, "grub2-menu", aarch64_distrotrees)


def main():
    parser = OptionParser(
        description="""Writes a netboot menu to the TFTP root
directory, containing distros from Beaker."""
    )
    parser.add_option(
        "--tag",
        metavar="TAG",
        action="append",
        dest="tags",
        help="Only include distros tagged with TAG",
    )
    parser.add_option(
        "--xml-filter",
        metavar="XML",
        help="Only include distro trees which match the given "
        "XML filter criteria, as in <distroRequires/>",
    )
    parser.add_option(
        "--tftp-root",
        metavar="DIR",
        default="/var/lib/tftpboot",
        help="Path to TFTP root directory [default: %default]",
    )
    parser.add_option(
        "-q", "--quiet", action="store_true", help="Suppress informational output"
    )
    (opts, args) = parser.parse_args()
    if args:
        parser.error("This command does not accept any arguments")
    if opts.quiet:
        os.dup2(os.open("/dev/null", os.O_WRONLY), 1)
    write_menus(opts.tftp_root, opts.tags, opts.xml_filter)
    return 0


if __name__ == "__main__":
    sys.exit(main())
