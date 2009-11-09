#!/usr/bin/python
# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or 
# redistribute it subject to the terms and conditions of the GNU General 
# Public License v.2.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Bill Peck
#

import sys, getopt
import xmlrpclib
import string
import os
import commands
import pprint
import math
import re

sys.path.append('.')
sys.path.append("/usr/lib/anaconda")
import smolt
import network
from disks import Disks
import isys

USAGE_TEXT = """
Usage:  push-inventory.py [-d] [[-h <HOSTNAME>] [-S server]]
"""

def push_inventory(hostname, inventory):
   session = xmlrpclib.Server(lab_server, allow_none=True)
   try:
      resp = getattr(session, method)(hostname, inventory)
      if(resp != 0) :
         raise NameError, "ERROR: Pushing Inventory for host %s." % hostname
   except:
      raise

def read_inventory():
    # get the data from SMOLT but modify it for how RHTS expects to see it
    # Eventually we'll switch over to SMOLT properly.
    data = {}
    data['MODULE'] = []
    data['CPUFLAGS'] = []
    data['PCIID'] = []
    data['USBID'] = []
    data['HVM'] = False
    data['DISK'] = []
    data['BOOTDISK'] = []
    data['DISKSPACE'] = 0
    data['NR_DISKS'] = 0
    data['NR_ETH'] = 0
    data['NR_IB'] = 0

    cpu_info = smolt.read_cpuinfo()
    memory   = smolt.read_memory()
    profile  = smolt.Hardware()

    data['ARCH'] = cpu_info['platform']
    data['CPUSPEED'] = cpu_info['speed']
    try:
        data['CPUFAMILY'] = cpu_info['model_number']
    except:
        try:
            data['CPUFAMILY'] = cpu_info['model_rev']
        except:
            pass 
    data['CPUVENDOR'] = cpu_info['type']
    data['CPUMODEL'] = cpu_info['model']
    data['CPUMODELNUMBER'] = cpu_info['model_ver']
    data['PROCESSORS'] = cpu_info['count']
    data['VENDOR'] = "%s" % profile.host.systemVendor
    data['MODEL'] = "%s" % profile.host.systemModel
    data['FORMFACTOR'] = "%s" % profile.host.formfactor

    # Round memory up to the next base 2
    n=0
    memory = int(memory['ram'])
    while memory > ( 2 << n):
        n=n+1
    data['MEMORY'] = 2 << n

    try:
        for cpuflag in cpu_info['other'].split(" "):
            data['CPUFLAGS'].append(cpuflag)
    except:
        pass

    for VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description in profile.deviceIter():
       if VendorID and DeviceID:
           if Bus == "pci":
               data['PCIID'].append("%04x:%04x" % ( VendorID, DeviceID))
           if Bus == "usb":
               data['USBID'].append("%04x:%04x" % ( VendorID, DeviceID))

    modules =  commands.getstatusoutput('/sbin/lsmod')[1].split('\n')[1:]
    for module in modules:
        data['MODULE'].append(module.split()[0])

    # Find Active Storage Driver(s)
    bootdisk = None
    bootregex = re.compile(r'/dev/([^ ]+) on /boot')
    disks = commands.getstatusoutput('/bin/mount')[1].split('\n')[1:]
    for disk in disks:
        if bootregex.search(disk):
            # Replace / with !, needed for cciss
            bootdisk = bootregex.search(disk).group(1).replace('/','!')

    if bootdisk:
        drivers = commands.getstatusoutput('./getdriver.sh %s' % bootdisk)[1].split('\n')[1:]
        for driver in drivers:
            data['BOOTDISK'].append(driver)

    # Find Active Network interface
    iface = None
    for line in  commands.getstatusoutput('route -n')[1].split('\n'):
        if line.find('0.0.0.0') == 0:
            iface = line.split()[-1:][0] #eth0, eth1, etc..
    if iface:
        driver = commands.getstatusoutput('./getdriver.sh %s' % iface)[1].split('\n')[1:][0]
        data['NETWORK'] = driver

    disks = Disks()
    data['DISK'] = disks.disks
    data['DISKSPACE'] = disks.diskspace
    data['NR_DISKS'] = disks.nr_disks

    # finding out eth and ib interfaces...
    eth_pat = re.compile ('^eth\d+$')
    ib_pat  = re.compile ('^ib\d+$')
    net = network.Network()
    for intname in net.available().keys():
        if isys.getLinkStatus(intname):
            if eth_pat.match(intname):
               data['NR_ETH'] += 1
            elif ib_pat.match(intname):
               data['NR_IB'] += 1

    # checking for whether or not the machine is hvm-enabled.
    caps = ""
    if os.path.exists("/sys/module/kvm_amd") or \
       os.path.exists("/sys/module/kvm_intel"):
           data['HVM'] = True

    return data

def usage():
    print USAGE_TEXT
    sys.exit(-1)

def main():
    global lab_server, hostname, method

    lab_server = None
    server = None
    hostname = None
    debug = 0
    method = "legacypush"
    rpc = "RPC2"

    if ('LAB_SERVER' in os.environ.keys()):
        server = os.environ['LAB_SERVER']
    if ('HOSTNAME' in os.environ.keys()):
        hostname = os.environ['HOSTNAME']

    args = sys.argv[1:]
    try:
        opts, args = getopt.getopt(args, 'dh:S:l', ['server=','legacy'])
    except:
        usage()
    for opt, val in opts:
        if opt in ('-l', '--legacy'):
            method = "machines.update"
            rpc = "cgi-bin/rhts/xmlrpc.cgi"
        if opt in ('-d', '--debug'):
            debug = 1
        if opt in ('-h', '--hostname'):
            hostname = val
        if opt in ('-S', '--server'):
            server = val

    lab_server = "%s/%s" % (server, rpc)
    inventory = read_inventory()
    if debug:
        print inventory
    else:
        if not hostname:
            print "You must specify a hostname with the -h switch"
            sys.exit(1)

        if not lab_server:
            print "You must specify a lab_server with the -S switch"
            sys.exit(1)

        push_inventory(hostname, inventory)


if __name__ == '__main__':
    main()
    sys.exit(0)

