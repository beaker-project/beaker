#!/usr/bin/python

import os
import glob
import sys

if len(sys.argv) < 3:
    print "Missing required arguments"
    sys.exit(1)

objtype = sys.argv[1] # "system" or "profile"
name    = sys.argv[2] # name of system or profile
ip      = sys.argv[3] # ip or "?"

filename = "/var/consoles/%s" % name
if os.path.isfile(filename):
    try:
        print "unlinking '%s'" % filename
        os.unlink(filename)
    except OSError, e:
        print "failed to unlink '%s'" % f

sys.exit(0)

