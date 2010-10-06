#!/usr/bin/python

import sys, getopt
from twill.commands import *

USAGE_TEXT = """
Usage: add_labcontroller.py -l labcontroller
"""
def usage():
    print USAGE_TEXT
    sys.exit(-1)

labcontroller = None
args = sys.argv[1:]
try:
    opts, args = getopt.getopt(args, 'l:', ['labcontroller='])
except:
    usage()

for opt, val in opts:
    if opt in ('-l', '--labcontroller'):
        labcontroller = val

if not labcontroller:
    usage()

# login
go("http://localhost/bkr/login")
formclear(1)
fv("1","user_name","admin")
fv("1","password","testing")
submit('login')

# Add lab controller
go("/bkr/labcontrollers/new")
code(200)
formclear(1)
fv("1","fqdn",labcontroller)
fv("1","username", "testing")
fv("1","password", "testing")
submit('5')
code(200)
