#!/usr/bin/python

import sys, getopt
from twill.commands import *

USAGE_TEXT = """
Usage: add_user.py -u user -p password
"""
def usage():
    print USAGE_TEXT
    sys.exit(-1)

user = None
password = ""
args = sys.argv[1:]
try:
    opts, args = getopt.getopt(args, 'u:p:', ['user=','password='])
except:
    usage()

for opt, val in opts:
    if opt in ('-u', '--user'):
        user = val
    if opt in ('-p', '--password'):
        password = val

if not user:
    usage()

# login
go("http://localhost/bkr/login")
formclear(1)
fv("1","user_name","admin")
fv("1","password","testing")
submit('login')

# Add user
go("/bkr/users/new")
code(200)
formclear(1)
fv("1","user_name", user)
fv("1","display_name", user)
fv("1","email_address", user)
fv("1","password", password)
submit()
code(200)
