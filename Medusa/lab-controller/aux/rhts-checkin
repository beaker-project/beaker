#!/usr/bin/python

"""
This is a script used to extend the install watchdog for rhts tests
and to report success on the initial start of the install

Copyright 2008, Red Hat, Inc
various@redhat.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import os
import sys
import string
import re

# on older installers (EL 2) we might not have xmlrpclib
# and can't do logging, however this is more widely
# supported than remote syslog and also provides more
# detail.
try:
    import xmlrpclib
except ImportError, e:
    print "xmlrpclib not available, exiting"
    sys.exit(0)

# Establish some defaults
name = ""
server = ""
recipeid = ""
port = "80"

# Process command-line args
n = 0
while n < len(sys.argv):
    arg = sys.argv[n]
    if arg == '--name':
        n = n+1
        name = sys.argv[n]
    elif arg == '--server':
        n = n+1
        server = sys.argv[n]
    elif arg == '--recipeid':
        n = n+1
        recipeid = sys.argv[n]
    n = n+1

# Create an xmlrpc session handle
session = xmlrpclib.Server("http://%s:%s/cgi-bin/rhts/scheduler_xmlrpc.cgi" % (server, port))

session.watchdog.installCheckin(name,recipeid)
sys.exit(0)
