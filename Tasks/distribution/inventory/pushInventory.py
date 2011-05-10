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
import glob

sys.path.append("/usr/share/smolt/client")
import smolt
import procfs

USAGE_TEXT = """
Usage:  push-inventory.py -h <HOSTNAME>
"""

def push_inventory(hostname, inventory):
   session = xmlrpclib.Server(lab_server, allow_none=True)
   try:
      resp = session.push(hostname, inventory)
      if(resp != 0) :
         raise NameError, "ERROR: Pushing Inventory for host %s." % hostname
   except:
      raise

def read_inventory():
    # get the data from SMOLT but modify it for how RHTS expects to see it
    # Eventually we'll switch over to SMOLT properly.
    data = {}
    flags = []
    data['Devices'] = []

    procCpu  = procfs.cpuinfo()
    smoltCpu = smolt.read_cpuinfo()
    memory   = smolt.read_memory()
    profile  = smolt.Hardware()

    arch = smoltCpu['platform']

    if arch in ["i386", "x86_64"]:
        for cpuflag in procCpu.tags['flags'].split(" "):
            flags.append(cpuflag)
        cpu = dict(vendor     = smoltCpu['type'],
                   model      = int(procCpu.tags['model']),
                   modelName  = smoltCpu['model'],
                   speed      = float(procCpu.tags['cpu mhz']),
                   processors = int(procCpu.nr_cpus),
                   cores      = int(procCpu.nr_cores),
                   sockets    = int(procCpu.nr_sockets),
                   CpuFlags   = flags,
                   family     = int(smoltCpu['model_number']),
                   stepping   = int(procCpu.tags['stepping']),
                  )
    elif arch in ["ppc", "ppc64"]:
        cpu = dict(vendor     = "IBM",
                   model      = str(procCpu.tags['machine']),
                   modelName  = str(procCpu.tags['cpu']),
                   speed      = str(procCpu.tags['clock']),
                   processors = int(procCpu.nr_cpus),
                   cores      = None,
                   sockets    = None,
                   CpuFlags   = flags,
                   family     = str(procCpu.tags['revision']),
                   stepping   = None,
                 )
    elif arch in ["s390", "s390x"]:
        for cpuflag in procCpu.tags['features'].split(" "):
            flags.append(cpuflag)
        proc = dict([tuple(s.strip() for s in kv.split('=')) for kv in procCpu.tags['processor 0'].split(',')])
        cpu = dict(vendor     = str(procCpu.tags['vendor_id']),
                   model      = str(proc['machine']),
                   modelName  = None,
                   processors = int(procCpu.tags['# processors']),
                   cores      = None,
                   sockets    = None,
                   CpuFlags   = flags,
                   family     = None,
                   speed      = None,
                   stepping   = None,
                  )
    elif arch == "ia64":
        for cpuflag in procCpu.tags['features'].split(","):
            flags.append(cpuflag.strip())
        cpu = dict(vendor     = smoltCpu['type'],
                   model      = int(procCpu.tags['model']),
                   modelName  = smoltCpu['model'],
                   speed      = float(procCpu.tags['cpu mhz']),
                   processors = int(procCpu.nr_cpus),
                   cores      = int(procCpu.nr_cores),
                   sockets    = int(procCpu.nr_sockets),
                   CpuFlags   = flags,
                   family     = int(smoltCpu['model_rev']),
                   stepping   = None,
                  )

    data['Cpu'] = cpu
    data['Arch'] = [arch]
    data['vendor'] = "%s" % profile.host.systemVendor
    data['model'] = "%s" % profile.host.systemModel
    #data['FORMFACTOR'] = "%s" % profile.host.formfactor
    data['memory'] = int(memory['ram'])
    if hasattr(profile.host, 'numaNodes'):
        data['Numa'] = {'nodes': profile.host.numaNodes}
    else:
        data['Numa'] = {
            'nodes': len(glob.glob('/sys/devices/system/node/node*')), #: number of NUMA nodes in the system, or 0 if not supported
        }

    for VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description in profile.deviceIter():
        device = dict ( vendorID = "%04x" % (VendorID and VendorID or 0),
                        deviceID = "%04x" % (DeviceID and DeviceID or 0),
                        subsysVendorID = "%04x" % (SubsysVendorID and SubsysVendorID or 0),
                        subsysDeviceID = "%04x" % (SubsysDeviceID and SubsysDeviceID or 0),
                        bus = Bus,
                        driver = Driver,
                        type = Type,
                        description = Description)
        data['Devices'].append(device)
    return data

def usage():
    print USAGE_TEXT
    sys.exit(-1)

def main():
    global lab_server, hostname

    lab_server = None
    hostname = None
    server = None
    debug = 0

    if ('LAB_SERVER' in os.environ.keys()):
        server = os.environ['LAB_SERVER']
    if ('HOSTNAME' in os.environ.keys()):
        hostname = os.environ['HOSTNAME']

    args = sys.argv[1:]
    try:
        opts, args = getopt.getopt(args, 'dh:S:', ['server='])
    except:
        usage()
    for opt, val in opts:
        if opt in ('-d', '--debug'):
            debug = 1
        if opt in ('-h', '--hostname'):
            hostname = val
        if opt in ('-S', '--server'):
            server = val

    if not hostname:
        print "You must sepcify a hostname with the -h switch"
        sys.exit(1)

    if not server:
        print "You must sepcify a lab_server with the -S switch"
        sys.exit(1)

    lab_server = "%s/RPC2" % (server)
    inventory = read_inventory()
    if debug:
        print inventory
    else:
        push_inventory(hostname, inventory)


if __name__ == '__main__':
    main()
    sys.exit(0)

