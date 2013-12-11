#!/usr/bin/env python
# Beaker - 
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# -*- coding: utf-8 -*-

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.log import log_to_stream
from bkr.server.model import (User, Group, Permission, Hypervisor, KernelType,
        Arch, PowerType, Key, Response, RetentionTag, ConfigItem)
from bkr.server.util import load_config
from turbogears.database import session
from os.path import dirname, exists, join
from os import getcwd
import turbogears
from turbogears.database import metadata, get_engine

from optparse import OptionParser

__version__ = '0.1'
__description__ = 'Command line tool for initializing Beaker DB'

def dummy():
    pass

def init_db(user_name=None, password=None, user_display_name=None, user_email_address=None):
    get_engine()
    metadata.create_all()
    session.begin()

    try:
        admin = Group.by_name(u'admin')
    except InvalidRequestError:
        admin     = Group(group_name=u'admin',display_name=u'Admin')

    try:
        lab_controller = Group.by_name(u'lab_controller')
    except InvalidRequestError:
        lab_controller = Group(group_name=u'lab_controller',
                               display_name=u'Lab Controller')
    
    #Setup User account
    if user_name:
        if password:
            user = User(user_name=user_name.decode('utf8'), password=password.decode('utf8'))
            if user_display_name:
                user.display_name = user_display_name.decode('utf8')
            if user_email_address:
                user.email_address = user_email_address.decode('utf8')
            admin.users.append(user)
        else:
            print "Password must be provided with username"
    elif len(admin.users) == 0:
        print "No admin account exists, please create one with --user"
        sys.exit(1)

    # Create distro_expire perm if not present
    try:
        distro_expire_perm = Permission.by_name(u'distro_expire')
    except NoResultFound:
        distro_expire_perm = Permission(u'distro_expire')

    # Create proxy_auth perm if not present
    try:
        proxy_auth_perm = Permission.by_name(u'proxy_auth')
    except NoResultFound:
        proxy_auth_perm = Permission(u'proxy_auth')

    # Create tag_distro perm if not present
    try:
        tag_distro_perm = Permission.by_name(u'tag_distro')
    except NoResultFound:
        tag_distro_perm = Permission(u'tag_distro')
        admin.permissions.append(tag_distro_perm)

    # Create stop_task perm if not present
    try:
        stop_task_perm = Permission.by_name(u'stop_task')
    except NoResultFound:
        stop_task_perm = Permission(u'stop_task')
        lab_controller.permissions.append(stop_task_perm)
        admin.permissions.append(stop_task_perm)

    # Create secret_visible perm if not present
    try:
        secret_visible_perm = Permission.by_name(u'secret_visible')
    except NoResultFound:
        secret_visible_perm = Permission(u'secret_visible')
        lab_controller.permissions.append(secret_visible_perm)
        admin.permissions.append(secret_visible_perm)

    #Setup Hypervisors Table
    if Hypervisor.query.count() == 0:
        kvm       = Hypervisor(hypervisor=u'KVM')
        xen       = Hypervisor(hypervisor=u'Xen')
        hyperv    = Hypervisor(hypervisor=u'HyperV')
        vmware    = Hypervisor(hypervisor=u'VMWare')

    #Setup kernel_type Table
    if KernelType.query.count() == 0:
        default  = KernelType(kernel_type=u'default', uboot=False)
        highbank = KernelType(kernel_type=u'highbank', uboot=False)
        imx      = KernelType(kernel_type=u'imx', uboot=False)
        mvebu    = KernelType(kernel_type=u'mvebu', uboot=True)
        omap     = KernelType(kernel_type=u'omap', uboot=False)
        tegra    = KernelType(kernel_type=u'tegra', uboot=False)

    #Setup base Architectures
    if Arch.query.count() == 0:
        i386   = Arch(u'i386')
        x86_64 = Arch(u'x86_64')
        ia64   = Arch(u'ia64')
        ppc    = Arch(u'ppc')
        ppc64  = Arch(u'ppc64')
        s390   = Arch(u's390')
        s390x  = Arch(u's390x')
        armhfp = Arch(u'armhfp')

    #Setup base power types
    if PowerType.query.count() == 0:
        apc_snmp    = PowerType(u'apc_snmp')
        PowerType(u'apc_snmp_then_etherwake')
        bladecenter = PowerType(u'bladecenter')
        bullpap     = PowerType(u'bladepap')
        drac        = PowerType(u'drac')
        ether_wake  = PowerType(u'ether_wake')
        PowerType(u'hyper-v')
        ilo         = PowerType(u'ilo')
        integrity   = PowerType(u'integrity')
        ipmilan     = PowerType(u'ipmilan')
        ipmitool    = PowerType(u'ipmitool')
        lpar        = PowerType(u'lpar')
        rsa         = PowerType(u'rsa')
        virsh       = PowerType(u'virsh')
        wti         = PowerType(u'wti')

    #Setup key types
    if Key.query.count() == 0:
        DISKSPACE       = Key(u'DISKSPACE',True)
        COMMENT         = Key(u'COMMENT')
        CPUFAMILY       = Key(u'CPUFAMILY',True)
        CPUFLAGS        = Key(u'CPUFLAGS')
        CPUMODEL        = Key(u'CPUMODEL')
        CPUMODELNUMBER  = Key(u'CPUMODELNUMBER', True)
        CPUSPEED        = Key(u'CPUSPEED',True)
        CPUVENDOR       = Key(u'CPUVENDOR')
        DISK            = Key(u'DISK',True)
        FORMFACTOR      = Key(u'FORMFACTOR')
        HVM             = Key(u'HVM')
        MEMORY          = Key(u'MEMORY',True)
        MODEL           = Key(u'MODEL')
        MODULE          = Key(u'MODULE')
        NETWORK         = Key(u'NETWORK')
        NR_DISKS        = Key(u'NR_DISKS',True)
        NR_ETH          = Key(u'NR_ETH',True)
        NR_IB           = Key(u'NR_IB',True)
        PCIID           = Key(u'PCIID')
        PROCESSORS      = Key(u'PROCESSORS',True)
        RTCERT          = Key(u'RTCERT')
        SCRATCH         = Key(u'SCRATCH')
        STORAGE         = Key(u'STORAGE')
        USBID           = Key(u'USBID')
        VENDOR          = Key(u'VENDOR')
        XENCERT         = Key(u'XENCERT')
        NETBOOT         = Key(u'NETBOOT_METHOD')

    #Setup ack/nak reposnses
    if Response.query.count() == 0:
        ACK      = Response(response=u'ack')
        NAK      = Response(response=u'nak')

    if RetentionTag.query.count() == 0:
        SCRATCH         = RetentionTag(tag=u'scratch', is_default=1, expire_in_days=30)
        SIXTYDAYS       = RetentionTag(tag=u'60days', needs_product=False, expire_in_days=60)
        ONETWENTYDAYS   = RetentionTag(tag=u'120days', needs_product=False, expire_in_days=120)
        ACTIVE          = RetentionTag(tag=u'active', needs_product=True)
        AUDIT           = RetentionTag(tag=u'audit', needs_product=True)

    config_items = [
        # name, description, numeric
        (u'root_password', u'Plaintext root password for provisioned systems', False),
        (u'root_password_validity', u"Maximum number of days a user's root password is valid for", True),
        (u'default_guest_memory', u"Default memory (MB) for dynamic guest provisioning", True),
        (u'default_guest_disk_size', u"Default disk size (GB) for dynamic guest provisioning", True),
        (u'guest_name_prefix', u'Prefix for names of dynamic guests in oVirt', False),
    ]
    for name, description, numeric in config_items:
        try:
            ConfigItem.by_name(name)
        except NoResultFound:
            ConfigItem(name=name, description=description, numeric=numeric)
    session.flush()
    if ConfigItem.by_name(u'root_password').current_value() is None:
        ConfigItem.by_name(u'root_password').set(u'beaker', user=admin.users[0])

    session.commit()
    session.close()

def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,
                          version=__version__)

    ## Actions
    parser.add_option("-c", "--config", action="store", type="string",
                      dest="configfile", help="location of config file.")
    parser.add_option("-u", "--user", action="store", type="string",
                      dest="user_name", help="username of Admin account")
    parser.add_option("-p", "--password", action="store", type="string",
                      dest="password", help="password of Admin account")
    parser.add_option("-e", "--email", action="store", type="string",
                      dest="email_address", 
                      help="email address of Admin account")
    parser.add_option("-n", "--fullname", action="store", type="string",
                      dest="display_name", help="Full name of Admin account")

    return parser

def main():
    parser = get_parser()
    opts, args = parser.parse_args()
    load_config(opts.configfile)
    log_to_stream(sys.stderr)
    init_db(user_name=opts.user_name, password=opts.password,
            user_display_name=opts.display_name,
            user_email_address=opts.email_address)

if __name__ == "__main__":
    main()
