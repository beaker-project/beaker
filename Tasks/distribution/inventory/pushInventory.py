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
import shutil
import glob
from subprocess import Popen, PIPE

sys.path.append('.')
sys.path.append("/usr/share/smolt/client")
import smolt
from disks import Disks
import procfs

USAGE_TEXT = """
Usage:  pushInventory.py [-d] [[-h <HOSTNAME>] [-S server]]
"""

def push_inventory(method, hostname, inventory):
   session = xmlrpclib.Server(lab_server, allow_none=True)
   try:
      resp = getattr(session, method)(hostname, inventory)
      if(resp != 0) :
         raise NameError, "ERROR: Pushing Inventory for host %s." % hostname
   except:
      raise

def check_for_virt_iommu():

    virt_iommu = 0
    cpu_info = smolt.read_cpuinfo()
    cpu_info_pat = re.compile("x86")

    if not cpu_info_pat.search(cpu_info['platform']):
        #only x86 boxes support virt iommu
        return 0

    #setup data directory
    path="acpiout"
    try:
        os.makedirs(path)
    except OSError:
        pass

    #find and extract data
    if not os.path.exists("acpidump") or not os.path.exists("acpixtract"):
        raise ("missing acpidump and/or acpixtract executables")
    os.chdir(path)
    os.system("../acpidump --output acpi.dump > /dev/null")
    os.system("../acpixtract -a acpi.dump > /dev/null")

    #test what type of system we are on
    if os.path.exists("DMAR.dat"):
        # alright we are on an Intel vt-d box
        hwu = False
        ba = False

        # create ascii file
        os.system("iasl -d DMAR.dat > /dev/null 2>&1")
        if os.path.exists("DMAR.dsl"):
            f = open("DMAR.dsl", 'r')

            #look for keywords to validate ascii file
            hwu_pat = re.compile ('Hardware Unit')
            ba_pat = re.compile ('Base Address')
            ba_inv_pat = re.compile ('0000000000000000|FFFFFFFFFFFFFFFF')

            for line in f.readlines():
                if hwu_pat.search(line):
                    hwu = True
                if ba_pat.search(line):
                    if ba_inv_pat.search(line):
                        print "VIRT_IOMMU: Invalid Base address: 0's or F's"
                    else:
                        ba = True
            if not hwu:
                print "VIRT_IOMMU: No Hardware Unit"
            elif not ba:
                print "VIRT_IOMMU: No Base Address"
            else:
                virt_iommu = 1
        else:
            print "VIRT_IOMMU: Failed to create DMAR.dsl"

    elif os.path.exists("IVRS.dat"):
        # alright we are on an AMD iommu box
        #  we don't have a good way to validate this
        virt_iommu = 1

    #clean up
    os.chdir("..")
    try:
        shutil.rmtree(path)
    except:
        print "VIRT_IOMMU: can't remove directory"

    return virt_iommu

def kernel_inventory():
    data = {}
    data['VIRT_IOMMU'] = False

    ##########################################
    # check for virtual iommu/vt-d capability
    # if this passes, assume we pick up sr-iov for free

    if check_for_virt_iommu():
        data['VIRT_IOMMU'] = True

    ##########################################
    # determine which stroage controller has a disk behind it
    path = "/sys/block"
    virt_pat = re.compile('virtual')
    floppy_pat = re.compile('fd[0-9]')
    sr_pat = re.compile('sr[0-9]')
    for block in glob.glob( os.path.join(path, '*')):
        #skip read only/floppy devices
        if sr_pat.search(block) or floppy_pat.search(block):
            continue

        #skip block devices that don't point to a device
        if not os.path.islink(block + "/device"):
            continue
        sysfs_link = os.readlink(block + "/device")

        #skip virtual devices
        if virt_pat.search(sysfs_link):
            continue

        #cheap way to create an absolute path, there is probably a better way
        sysfs_path = sysfs_link.replace('../..','/sys')

        #start abusing hal to give us the info we want
        cmd = 'hal-find-by-property --key linux.sysfs_path --string %s' % sysfs_path
        status,udi =  commands.getstatusoutput(cmd)
        if status:
            print "DISK_CONTROLLER: hal-find-by-property failed: %d" % status
            continue

        while udi:
            cmd = 'hal-get-property --udi %s --key info.linux.driver 2>/dev/null' % udi
            status, driver = commands.getstatusoutput(cmd)
            if status == 0 and driver != "sd" and driver != "sr":
                #success
                data['DISK_CONTROLLER'] = driver
                break

            #get the parent and try again
            cmd = 'hal-get-property --udi %s  --key info.parent' % udi
            status,udi =  commands.getstatusoutput(cmd)
            if status:
                print "DISK_CONTROLLER: hal-get-property failed: %d" % status
                break

        if not udi:
            print "DISK_CONTROLLER: can not determine driver for %s" %block

    ##########################################
    # determine if machine is using multipath or not

    #ok, I am really lazy
    #remove the default blacklist in /etc/multipath.conf
    os.system("sed -i '/^blacklist/,/^}$/d' /etc/multipath.conf")

    #restart multipathd to see what it detects
    #this spits out errors if the root device is on a
    #multipath device, I guess ignore for now and hope the code
    #correctly figures things out
    os.system("service multipathd restart")

    #the multipath commands will display the topology if it
    #exists otherwise nothing
    #filter out vbds and single device paths
    status, mpaths = commands.getstatusoutput("multipath -ll")
    mp = False
    if status:
        print "MULTIPATH: multipath -ll failed with %d" % status
    else:
        count = 0
        mpath_pat = re.compile(" dm-[0-9]* ")
        sd_pat = re.compile(" sd[a-z]")
        for line in mpaths.split('\n'):
            #reset when a new section starts
            if mpath_pat.search(line):
                # found at least one mp instance, declare success
                if count > 1:
                    mp = True
                    break
                count = 0

            #a hit! increment to indicate this
            if sd_pat.search(line):
                count = count + 1

    if mp == True:
        data['DISK_MULTIPATH'] = True
    else:
        data['DISK_MULTIPATH'] = False

    return data

def legacy_inventory(inv):
    # Take the gathered inventory data, fill legacy key/value schema with it
    # and gather any missing bits.
    data = {}
    data['MODULE'] = []
    data['HVM'] = False
    data['DISK'] = []
    data['BOOTDISK'] = []
    data['DISKSPACE'] = 0
    data['NR_DISKS'] = 0
    data['NR_ETH'] = 0
    data['NR_IB'] = 0

    data['ARCH'] = inv['Arch'][0]
    data['CPUSPEED'] = int(inv['Cpu']['speed'])
    data['CPUFAMILY'] = "%s" % inv['Cpu']['family']
    data['CPUVENDOR'] = inv['Cpu']['vendor']
    data['CPUMODEL'] = inv['Cpu']['modelName']
    data['CPUMODELNUMBER'] = "%s" % inv['Cpu']['model']
    data['PROCESSORS'] = inv['Cpu']['processors']
    data['VENDOR'] = inv['vendor']
    data['MODEL'] = inv['model']
    data['FORMFACTOR'] = inv['formfactor']
    data['CPUFLAGS'] = inv['Cpu']['CpuFlags']
    data['PCIID'] = ["%s:%s" % (d['vendorID'], d['deviceID']) for d in inv['Devices'] if d['bus'] == 'pci']
    data['USBID'] = ["%s:%s" % (d['vendorID'], d['deviceID']) for d in inv['Devices'] if d['bus'] == 'usb']

    # The below data (and kernel_inventory()) has not (yet) made it to the new schema
    # (and formfactor above)

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
        drivers = commands.getstatusoutput('./getdriver.sh %s' % iface)[1].split('\n')
        if len(drivers) == 1:
            data['NETWORK'] = drivers[0]
        else:
            data['NETWORK'] = drivers[1:][0]

    disks = Disks()
    data['DISK'] = disks.disks
    data['DISKSPACE'] = disks.diskspace
    data['NR_DISKS'] = disks.nr_disks

    # finding out eth and ib interfaces...
    eth_pat = re.compile ('^ *eth\d+:')
    ib_pat  = re.compile ('^ *ib\d+:')
    for line in open("/proc/net/dev", "r"):
        if eth_pat.match(line):
           data['NR_ETH'] += 1
        elif ib_pat.match(line):
           data['NR_IB'] += 1

    # checking for whether or not the machine is hvm-enabled.
    caps = ""
    if os.path.exists("/sys/module/kvm_amd") or \
       os.path.exists("/sys/module/kvm_intel"):
           data['HVM'] = True
    elif os.path.exists('/proc/pal/cpu0/processor_info'): # ia64
        for line in open('/proc/pal/cpu0/processor_info', 'r'):
            if re.match('Virtual machine features.*: On', line):
                data['HVM'] = True

    return data

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
    data['formfactor'] = "%s" % profile.host.formfactor
    data['memory'] = int(memory['ram'])
    if hasattr(profile.host, 'numaNodes'):
        data['Numa'] = {'nodes': profile.host.numaNodes}
    else:
        data['Numa'] = {
            'nodes': len(glob.glob('/sys/devices/system/node/node*')), #: number of NUMA nodes in the system, or 0 if not supported
        }

    if os.path.exists('./hvm_detect'):
        hypervisor = Popen(['./hvm_detect'], stdout=PIPE).communicate()[0]
        hvm_map = {"No KVM or Xen HVM\n"    : None,
                   "KVM guest.\n"           : u'KVM',
                   "Xen HVM guest.\n"       : u'Xen',
                   "Microsoft Hv guest.\n"  : u'HyperV',
                   "VMWare guest.\n"        : u'VMWare',
                  }
        data['Hypervisor'] = hvm_map[hypervisor]

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
    debug = 0

    if ('LAB_SERVER' in os.environ.keys()):
        lab_server = os.environ['LAB_SERVER']
    if ('HOSTNAME' in os.environ.keys()):
        hostname = os.environ['HOSTNAME']

    args = sys.argv[1:]
    try:
        opts, args = getopt.getopt(args, 'dh:S', ['server='])
    except:
        usage()
    for opt, val in opts:
        if opt in ('-d', '--debug'):
            debug = 1
        if opt in ('-h', '--hostname'):
            hostname = val
        if opt in ('-S', '--server'):
            lab_server = val

    inventory = read_inventory()
    legacy_inv = legacy_inventory(inventory)
    legacy_inv.update(kernel_inventory())
    del inventory['formfactor']
    if debug:
        print "Legacy inventory:\n%s\nData:\n%s" % (legacy_inv, inventory)
    else:
        if not hostname:
            print "You must specify a hostname with the -h switch"
            sys.exit(1)

        if not lab_server:
            print "You must specify a lab_server with the -S switch"
            sys.exit(1)

        push_inventory("legacypush", hostname, legacy_inv)
        push_inventory("push", hostname, inventory)


if __name__ == '__main__':
    main()
    sys.exit(0)

