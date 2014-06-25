
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import string
import sys
import os, os.path
import errno
import xmlrpclib
import shutil
import urllib2
import urlparse
import contextlib
from optparse import OptionParser
from bkr.common.helpers import atomically_replaced_file, siphon, makedirs_ignore, atomic_symlink

def _get_url(available):
    for lc, url in available:
        # We prefer http
        if url.startswith('http:'):
            return url
    for lc, url in available:
        if url.startswith('ftp:'):
            return url

def _group_distro_trees(distro_trees):
    grouped = {}
    for dt in distro_trees:
        grouped.setdefault(dt['distro_osmajor'], {})\
            .setdefault(dt['distro_osversion'], [])\
            .append(dt)
    return grouped

def _get_images(tftp_root, distro_tree_id, url, images):
    dest_dir = os.path.join(tftp_root, 'distrotrees', str(distro_tree_id))
    makedirs_ignore(dest_dir, mode=0755)
    for image_type, path in images:
        if image_type in ('kernel', 'initrd'):
            dest_path = os.path.join(dest_dir, image_type)
            if os.path.isfile(dest_path):
                print 'Skipping existing %s for distro tree %s' % (image_type, distro_tree_id)
            else:
                image_url = urlparse.urljoin(url, path)
                print 'Fetching %s %s for distro tree %s' % (image_type, image_url, distro_tree_id)
                with atomically_replaced_file(dest_path) as dest:
                    siphon(urllib2.urlopen(image_url), dest)

pxe_menu_entry_template = string.Template('''
label ${distro_name}-${variant}-${arch}
    menu title ${distro_name} ${variant} ${arch}
    kernel /distrotrees/${distro_tree_id}/kernel
    append initrd=/distrotrees/${distro_tree_id}/initrd method=${url} repo=${url} ${kernel_options}
''')

efi_menu_entry_template = string.Template('''
title ${distro_name} ${variant} ${arch}
    root (nd)
    kernel /distrotrees/${distro_tree_id}/kernel method=${url} repo=${url}
    initrd /distrotrees/${distro_tree_id}/initrd
''')

aarch64_menu_entry_template = string.Template('''
menuentry "${distro_name} ${variant} ${arch}" {
    linux /distrotrees/${distro_tree_id}/kernel method=${url} repo=${url}
    initrd /distrotrees/${distro_tree_id}/initrd
}
''')

def write_menus(tftp_root, tags, xml_filter):
    # The order of steps for cleaning images is important,
    # to avoid races and to avoid deleting stuff we shouldn't:
    # first read the directory,
    # then fetch the list of trees,
    # and then remove any which aren't in the list.
    try:
        existing_tree_ids = os.listdir(os.path.join(tftp_root, 'distrotrees'))
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise
        existing_tree_ids = []

    proxy = xmlrpclib.ServerProxy('http://localhost:8000', allow_none=True)
    x86_distrotrees = proxy.get_distro_trees({
        'arch': ['x86_64', 'i386'],
        'tags': tags,
        'xml': xml_filter,
    })
    aarch64_distrotrees = proxy.get_distro_trees({
        'arch': ['aarch64'],
        'tags': tags,
        'xml': xml_filter,
    })

    current_tree_ids = set(str(dt['distro_tree_id'])
            for dt in x86_distrotrees + aarch64_distrotrees)
    obsolete_tree_ids = set(existing_tree_ids).difference(current_tree_ids)
    print 'Removing images for %s obsolete distro trees' % len(obsolete_tree_ids)
    for obs in obsolete_tree_ids:
        shutil.rmtree(os.path.join(tftp_root, 'distrotrees', obs), ignore_errors=True)

    print 'Generating PXELINUX and EFI GRUB menus for %s distro trees' % len(x86_distrotrees)
    osmajors = _group_distro_trees(x86_distrotrees)
    makedirs_ignore(os.path.join(tftp_root, 'pxelinux.cfg'), mode=0755)
    pxe_menu = atomically_replaced_file(os.path.join(tftp_root, 'pxelinux.cfg', 'beaker_menu'))
    makedirs_ignore(os.path.join(tftp_root, 'grub'), mode=0755)
    atomic_symlink('../distrotrees', os.path.join(tftp_root, 'grub', 'distrotrees'))
    efi_menu = atomically_replaced_file(os.path.join(tftp_root, 'grub', 'efidefault'))
    with contextlib.nested(pxe_menu, efi_menu) as (pxe_menu, efi_menu):
        pxe_menu.write('''default menu
prompt 0
timeout 6000
ontimeout local
menu title Beaker
label local
    menu label (local)
    menu default
    localboot 0
''')

        for osmajor, osversions in sorted(osmajors.iteritems(), reverse=True):
            print 'Writing submenu %s' % osmajor
            pxe_menu.write('''
menu begin
menu title %s
''' % osmajor)
            for osversion, distro_trees in sorted(osversions.iteritems(), reverse=True):
                print 'Writing submenu %s -> %s' % (osmajor, osversion)
                pxe_menu.write('''
menu begin
menu title %s
''' % osversion)
                for distro_tree in distro_trees:
                    url = _get_url(distro_tree['available'])
                    try:
                        _get_images(tftp_root, distro_tree['distro_tree_id'],
                                url, distro_tree['images'])
                    except IOError, e:
                        sys.stderr.write('Error fetching images for distro tree %s: %s\n' %
                                (distro_tree['distro_tree_id'], e))
                    else:
                        print 'Writing menu entry for distro tree %s' % distro_tree['distro_tree_id']
                        pxe_menu.write(pxe_menu_entry_template.substitute(
                                distro_tree, url=url))
                        efi_menu.write(efi_menu_entry_template.substitute(
                                distro_tree, url=url))
                pxe_menu.write('''
menu end
''')
            pxe_menu.write('''
menu end
''')

    if aarch64_distrotrees:
        print 'Generating aarch64 menu for %s distro trees' % len(aarch64_distrotrees)
        osmajors = _group_distro_trees(aarch64_distrotrees)
        makedirs_ignore(os.path.join(tftp_root, 'aarch64'), mode=0755)
        aarch64_menu = atomically_replaced_file(os.path.join(tftp_root, 'aarch64', 'beaker_menu.cfg'))
        with aarch64_menu as aarch64_menu:
            aarch64_menu.write('''set default="Exit PXE"
set timeout=60
menuentry "Exit PXE" {
    exit
}
''')

            for osmajor, osversions in sorted(osmajors.iteritems(), reverse=True):
                print 'Writing submenu %s' % osmajor
                aarch64_menu.write('\nsubmenu "%s" {\n' % osmajor)
                for osversion, distro_trees in sorted(osversions.iteritems(), reverse=True):
                    print 'Writing submenu %s -> %s' % (osmajor, osversion)
                    aarch64_menu.write('\nsubmenu "%s" {\n' % osversion)
                    for distro_tree in distro_trees:
                        url = _get_url(distro_tree['available'])
                        try:
                            _get_images(tftp_root, distro_tree['distro_tree_id'],
                                    url, distro_tree['images'])
                        except IOError, e:
                            sys.stderr.write('Error fetching images for distro tree %s: %s\n' %
                                    (distro_tree['distro_tree_id'], e))
                        else:
                            print 'Writing menu entry for distro tree %s' % distro_tree['distro_tree_id']
                            aarch64_menu.write(aarch64_menu_entry_template.substitute(
                                    distro_tree, url=url))
                    aarch64_menu.write('\n}\n')
                aarch64_menu.write('\n}\n')

def main():
    parser = OptionParser(description='''Writes a netboot menu to the TFTP root
directory, containing distros from Beaker.''')
    parser.add_option('--tag', metavar='TAG', action='append', dest='tags',
            help='Only include distros tagged with TAG')
    parser.add_option('--xml-filter', metavar='XML',
            help='Only include distro trees which match the given '
            'XML filter criteria, as in <distroRequires/>')
    parser.add_option('--tftp-root', metavar='DIR',
            default='/var/lib/tftpboot',
            help='Path to TFTP root directory [default: %default]')
    parser.add_option('-q', '--quiet', action='store_true',
            help='Suppress informational output')
    (opts, args) = parser.parse_args()
    if args:
        parser.error('This command does not accept any arguments')
    if opts.quiet:
        os.dup2(os.open('/dev/null', os.O_WRONLY), 1)
    write_menus(opts.tftp_root, opts.tags, opts.xml_filter)
    return 0

if __name__ == '__main__':
    sys.exit(main())
