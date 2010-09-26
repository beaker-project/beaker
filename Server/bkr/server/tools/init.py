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

import sys
import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
from bkr.server.model import *
from bkr.server.commands import ConfigurationError
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

def main():
    parser = get_parser()
    opts, args = parser.parse_args()
    setupdir = dirname(dirname(__file__))
    curdir = getcwd()

    # First look on the command line for a desired config file,
    # if it's not on the command line, then look for 'setup.py'
    # in the current directory. If there, load configuration
    # from a file called 'dev.cfg'. If it's not there, the project
    # is probably installed and we'll look first for a file called
    # 'prod.cfg' in the current directory and then for a default
    # config file called 'default.cfg' packaged in the egg.
    load_config(opts.configfile)

    get_engine()
    metadata.create_all()

    #Setup ReleaseAction Table
    if ReleaseAction.query().count() == 0:
        poweroff    = ReleaseAction(u'PowerOff')
        leaveon     = ReleaseAction(u'LeaveOn')
        reprovision = ReleaseAction(u'ReProvision')

    #Setup SystemStatus Table
    if SystemStatus.query().count() == 0:
        automated   = SystemStatus(u'Automated')
        broken      = SystemStatus(u'Broken')
        removed     = SystemStatus(u'Removed')
        manual      = SystemStatus(u'Manual')
    try:
        admin = Group.by_name(u'admin')
    except InvalidRequestError:
        admin     = Group(group_name=u'admin',display_name=u'Admin')
    
    #Setup User account
    if opts.user_name:
        if opts.password:
            user = User(user_name=opts.user_name,
                        password=opts.password)
            if opts.display_name:
                user.display_name = opts.display_name
            if opts.email_address:
                user.email_address = opts.email_address
            admin.users.append(user)
        else:
            print "Password must be provided with username"

    #Setup SystemTypes Table
    if SystemType.query().count() == 0:
        machine   = SystemType(u'Machine')
        virtual   = SystemType(u'Virtual')
        resource  = SystemType(u'Resource')
        laptop    = SystemType(u'Laptop')
        prototype = SystemType(u'Prototype')

    #Setup base Architectures
    if Arch.query().count() == 0:
        i386   = Arch(u'i386')
        x86_64 = Arch(u'x86_64')
        ia64   = Arch(u'ia64')
        ppc    = Arch(u'ppc')
        ppc64  = Arch(u'ppc64')
        s390   = Arch(u's390')
        s390x  = Arch(u's390x')

    #Setup base power types
    if PowerType.query().count() == 0:
        apc_snmp    = PowerType(u'apc_snmp')
        bladecenter = PowerType(u'bladecenter')
        bullpap     = PowerType(u'bladepap')
        drac        = PowerType(u'drac')
        ether_wake  = PowerType(u'ether_wake')
        ilo         = PowerType(u'ilo')
        integrity   = PowerType(u'integrity')
        ipmilan     = PowerType(u'ipmilan')
        ipmitool    = PowerType(u'ipmitool')
        lpar        = PowerType(u'lpar')
        rsa         = PowerType(u'rsa')
        virsh       = PowerType(u'virsh')
        wti         = PowerType(u'wti')

    #Setup key types
    if Key.query().count() == 0:
        DISKSPACE       = Key('DISKSPACE',True)
        COMMENT         = Key('COMMENT')
        CPUFAMILY	= Key('CPUFAMILY',True)
        CPUFLAGS	= Key('CPUFLAGS')
        CPUMODEL	= Key('CPUMODEL')
        CPUMODELNUMBER 	= Key('CPUMODELNUMBER', True)
        CPUSPEED	= Key('CPUSPEED',True)
        CPUVENDOR	= Key('CPUVENDOR')
        DISK		= Key('DISK',True)
        FORMFACTOR 	= Key('FORMFACTOR')
        HVM		= Key('HVM')
        MEMORY		= Key('MEMORY',True)
        MODEL		= Key('MODEL')
        MODULE		= Key('MODULE')
        NETWORK		= Key('NETWORK')
        NR_DISKS	= Key('NR_DISKS',True)
        NR_ETH		= Key('NR_ETH',True)
        NR_IB		= Key('NR_IB',True)
        PCIID		= Key('PCIID')
        PROCESSORS	= Key('PROCESSORS',True)
        RTCERT		= Key('RTCERT')
        SCRATCH		= Key('SCRATCH')
        STORAGE		= Key('STORAGE')
        USBID		= Key('USBID')
        VENDOR		= Key('VENDOR')
        XENCERT		= Key('XENCERT')

    if TaskPriority.query().count() == 0:
        low             = TaskPriority(priority=u'Low')
        medium          = TaskPriority(priority=u'Medium')
        normal          = TaskPriority(priority=u'Normal')
        high            = TaskPriority(priority=u'High')
        urgent          = TaskPriority(priority=u'Urgent')

    #Setup Test Status
    if TaskStatus.query().count() == 0:
        NEW       = TaskStatus(status=u'New', severity=10)
        PROCESSED = TaskStatus(status=u'Processed', severity=20)
        QUEUEUD   = TaskStatus(status=u'Queued', severity=30)
        SCHEDULED = TaskStatus(status=u'Scheduled', severity=40)
        # RUNNING and WAITING are transient states.  It will never be final.
        #  But having it the lowest Severity will show a job as 
        #  Running until it finishes with either Completed, Cancelled or 
        #  Aborted.
        WAITING   = TaskStatus(status=u'Waiting', severity=7)
        RUNNING   = TaskStatus(status=u'Running', severity=5)
        COMPLETED = TaskStatus(status=u'Completed', severity=50)
        CANCELLED = TaskStatus(status=u'Cancelled', severity=60)
        ABORTED   = TaskStatus(status=u'Aborted', severity=70)

    #Setup Test Result
    if TaskResult.query().count() == 0:
        NEW       = TaskResult(result=u'New', severity=10)
        PASS      = TaskResult(result=u'Pass', severity=20)
        WARN      = TaskResult(result=u'Warn', severity=30)
        FAIL      = TaskResult(result=u'Fail', severity=40)
        PANIC     = TaskResult(result=u'Panic', severity=50)

    #Setup ack/nak reposnses
    if Response.query().count() == 0:
        ACK      = Response(response=u'ack')
        NAK      = Response(response=u'nak')

    if RetentionTag.query().count() == 0:
        SCRATCH         = RetentionTag(tag='scratch', is_default=1)
        SIXTYDAYS       = RetentionTag(tag='60days')
        ONETWENTYDAYS   = RetentionTag(tag='120days')
        ACTIVE          = RetentionTag(tag='active')
        AUDIT           = RetentionTag(tag='audit')
        
    session.flush()

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

if __name__ == "__main__":
    main()
