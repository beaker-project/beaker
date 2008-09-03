#!/usr/bin/python
# Logan - Logan is the scheduling piece of the Beaker project
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
from logan.model import *
from logan.commands import ConfigurationError
from turbogears.database import session
from os.path import dirname, exists, join
from os import getcwd
import turbogears

if __name__ == "__main__":
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
    elif exists(join(curdir, "prod.cfg")):
        configfile = join(curdir, "prod.cfg")
    else:
        try:
            configfile = pkg_resources.resource_filename(
              pkg_resources.Requirement.parse("logan"),
                "config/default.cfg")
        except pkg_resources.DistributionNotFound:
            raise ConfigurationError("Could not find default configuration.")

    turbogears.update_config(configfile=configfile,
        modulename="logan.config")

    #Setup Status table
    if Status.query().count() == 0:
        queued    = Status(u'Queued')
        running   = Status(u'Running')
        completed = Status(u'Completed')
        canceled  = Status(u'Canceled')
    #Setup Result table
    if Result.query().count() == 0:
        aborted   = Result(u'Aborted')
        rpass     = Result(u'Pass')
        none      = Result(u'N/A')
        warn      = Result(u'Warn')
        fail      = Result(u'Fail')
        panic     = Result(u'Panic')
    #Setup Priority table
    if Priority.query().count() == 0:
        low       = Priority(u'Low')
        medium    = Priority(u'Medium')
        normal    = Priority(u'Normal')
        high      = Priority(u'High')
        urgent    = Priority(u'Urgent')
    #Setup User account
    if User.query().count() == 0:
        user     = User(display_name=u'Test User',
                         email_address=u'test@domain.com',
                         password=u'password',
                         user_name=u'tuser')
        admin     = Group(group_name=u'admin')
        admin.users.append(user)
    #Setup Arch Table
    if Arch.query().count() == 0:
        i386        = Arch(u'i386')   
        x86_64      = Arch(u'x86_64')   
        ia64        = Arch(u'ia64')   
        ppc         = Arch(u'ppc')
        s390        = Arch(u's390')
        s390x       = Arch(u's390x')
        #Setup Family Table
        fedora9     = Family(u'Fedora9',u'F9')
        fedora9.arches.append(i386)
        fedora9.arches.append(x86_64)
        fedora9.arches.append(ppc)
        fedora10    = Family(u'Fedora10',u'F10')
        fedora10.arches.append(i386)
        fedora10.arches.append(x86_64)
        rhel3       = Family(u'RedHatEnterpriseLinux3',u'RHEL3')
        rhel3.arches.append(i386)
        rhel3.arches.append(x86_64)
        rhel3.arches.append(ia64)
        rhel3.arches.append(ppc)
        rhel3.arches.append(s390)
        rhel3.arches.append(s390x)
        rhel4       = Family(u'RedHatEnterpriseLinux4',u'RHEL4')
        rhel4.arches.append(i386)
        rhel4.arches.append(x86_64)
        rhel4.arches.append(ia64)
        rhel4.arches.append(ppc)
        rhel4.arches.append(s390)
        rhel4.arches.append(s390x)
        rhelclient5 = Family(u'RedHatEnterpriseLinuxClient',u'RHELClient5')
        rhelclient5.arches.append(i386)
        rhelclient5.arches.append(x86_64)
        rhelserver5 = Family(u'RedHatEnterpriseLinuxServer5',u'RHELServer5')
        rhelserver5.arches.append(i386)
        rhelserver5.arches.append(x86_64)
        rhelserver5.arches.append(ia64)
        rhelserver5.arches.append(ppc)
        rhelserver5.arches.append(s390x)

    session.flush()
