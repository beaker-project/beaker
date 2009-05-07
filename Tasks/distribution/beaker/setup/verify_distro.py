#!/usr/bin/python

import sys, getopt
from twill.commands import *

USAGE_TEXT = """
Usage: verify_distro.py -s Inventory -d distro_name -f family -u update
"""
def usage():
    print USAGE_TEXT
    sys.exit(-1)

server = None
args = sys.argv[1:]
try:
    opts, args = getopt.getopt(args, 's:d:f:u:', ['server='])
except:
    usage()

for opt, val in opts:
    if opt in ('-s', '--server'):
        server = val
    if opt in ('-d'):
        distro = val
    if opt in ('-f'):
        family = val
    if opt in ('-u'):
        update = val

if not server:
    usage()

# login
go("https://%s/login" % server)
formclear(1)
fv("1","user_name","admin")
fv("1","password","testing")
submit('login')

# Verify Added Distros
go("/distros/?name=%s" % distro)
code(200)
find("%s.*</td><td>redhat</td><td>%s</td><td>%s" % (distro, family, update))
