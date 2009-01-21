#!/usr/bin/env python
# Medusa - Medusa is the Lab Contrller piece of the Beaker project
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
from medusa.model import *
from medusa.commands import ConfigurationError
from turbogears.database import session
from os.path import dirname, exists, join
from os import getcwd
import turbogears
from turbogears.database import metadata, get_engine

def dummy():
    pass

def main():
    setupdir = dirname(dirname(__file__))
    curdir = getcwd()

    # First look on the command line for a desired config file,
    # if it's not on the command line, then look for 'setup.py'
    # in the current directory. If there, load configuration
    # from a file called 'dev.cfg'. If it's not there, the project
    # is probably installed and we'll look first for a file called
    # 'prod.cfg' in the current directory and then for a default
    # config file called 'default.cfg' packaged in the egg.
    if len(sys.argv) > 1:
        configfile = sys.argv[1]
    elif exists(join(setupdir, "setup.py")):
        configfile = join(setupdir, "dev.cfg")
    elif exists("/etc/medusa/medusa.cfg"):
        configfile = "/etc/medusa/medusa.cfg"
    else:
        try:
            configfile = pkg_resources.resource_filename(
              pkg_resources.Requirement.parse("medusa"),
                "config/default.cfg")
        except pkg_resources.DistributionNotFound:
            raise ConfigurationError("Could not find default configuration.")

    turbogears.update_config(configfile=configfile,
        modulename="medusa.config")

    get_engine()
    metadata.create_all()

    #Setup SystemStatus Table
    if SystemStatus.query().count() == 0:
        working   = SystemStatus(u'Working')
        broken    = SystemStatus(u'Broken')
        removed   = SystemStatus(u'Removed')
    #Setup User account
    if User.query().count() == 0:
        user     = User(display_name=u'Bill Peck',
                         email_address=u'bpeck@redhat.com',
                         user_name=u'bpeck')
        admin     = Group(group_name=u'admin',display_name=u'Admin')
        admin.users.append(user)

    #Setup SystemTypes Table
    if SystemType.query().count() == 0:
        machine   = SystemType(u'Machine')
        virtual   = SystemType(u'Virtual')
        resource  = SystemType(u'Resource')

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

    session.flush()

if __name__ == "__main__":
    main()
