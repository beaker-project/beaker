#!/usr/bin/python
# -*- coding: latin-1 -*-

# smolt - Fedora hardware profiler
#
# Copyright (C) 2007 Mike McGrath
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
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

######################################################
# This class is a basic wrapper for the dbus bindings
# 
# I have completely destroyed this file, it needs some cleanup
# - mmcgrath
######################################################
# TODO
#
# Abstract "type" in device class
# Find out what we're not getting
#

from i18n import _

import dbus
import software
import os
import urlgrabber.grabber
import sys
from urlparse import urljoin
from urllib import urlencode

smoonURL = 'http://smolt.fedoraproject.org/'
smoltProtocol = '.91'
user_agent = 'smolt/%s' % smoltProtocol
timeout = 60.0
DEBUG = False

PCI_BASE_CLASS_STORAGE =        1
PCI_CLASS_STORAGE_SCSI =        0
PCI_CLASS_STORAGE_IDE =         1
PCI_CLASS_STORAGE_FLOPPY =      2
PCI_CLASS_STORAGE_IPI =         3
PCI_CLASS_STORAGE_RAID =        4
PCI_CLASS_STORAGE_OTHER =       80

PCI_BASE_CLASS_NETWORK =        2
PCI_CLASS_NETWORK_ETHERNET =    0
PCI_CLASS_NETWORK_TOKEN_RING =  1
PCI_CLASS_NETWORK_FDDI =        2
PCI_CLASS_NETWORK_ATM =         3
PCI_CLASS_NETWORK_OTHER =       80
PCI_CLASS_NETWORK_WIRELESS =    128

PCI_BASE_CLASS_DISPLAY =        3
PCI_CLASS_DISPLAY_VGA =         0
PCI_CLASS_DISPLAY_XGA =         1
PCI_CLASS_DISPLAY_3D =          2
PCI_CLASS_DISPLAY_OTHER =       80

PCI_BASE_CLASS_MULTIMEDIA =     4
PCI_CLASS_MULTIMEDIA_VIDEO =    0
PCI_CLASS_MULTIMEDIA_AUDIO =    1
PCI_CLASS_MULTIMEDIA_PHONE =    2
PCI_CLASS_MULTIMEDIA_OTHER =    80

PCI_BASE_CLASS_BRIDGE =         6
PCI_CLASS_BRIDGE_HOST =         0
PCI_CLASS_BRIDGE_ISA =          1
PCI_CLASS_BRIDGE_EISA =         2
PCI_CLASS_BRIDGE_MC =           3
PCI_CLASS_BRIDGE_PCI =          4
PCI_CLASS_BRIDGE_PCMCIA =       5
PCI_CLASS_BRIDGE_NUBUS =        6
PCI_CLASS_BRIDGE_CARDBUS =      7
PCI_CLASS_BRIDGE_RACEWAY =      8
PCI_CLASS_BRIDGE_OTHER =        80

PCI_BASE_CLASS_COMMUNICATION =  7
PCI_CLASS_COMMUNICATION_SERIAL = 0
PCI_CLASS_COMMUNICATION_PARALLEL = 1
PCI_CLASS_COMMUNICATION_MULTISERIAL = 2
PCI_CLASS_COMMUNICATION_MODEM = 3
PCI_CLASS_COMMUNICATION_OTHER = 80

PCI_BASE_CLASS_INPUT =          9
PCI_CLASS_INPUT_KEYBOARD =      0
PCI_CLASS_INPUT_PEN =           1
PCI_CLASS_INPUT_MOUSE =         2
PCI_CLASS_INPUT_SCANNER =       3
PCI_CLASS_INPUT_GAMEPORT =      4
PCI_CLASS_INPUT_OTHER =         80

PCI_BASE_CLASS_SERIAL =         12
PCI_CLASS_SERIAL_FIREWIRE =     0
PCI_CLASS_SERIAL_ACCESS =       1

PCI_CLASS_SERIAL_SSA =          2
PCI_CLASS_SERIAL_USB =          3
PCI_CLASS_SERIAL_FIBER =        4
PCI_CLASS_SERIAL_SMBUS =        5

class Device:
    def __init__(self, props):
        self.UUID = getUUID()
        try:
            self.bus = props['linux.subsystem'].strip()
        except KeyError:
            self.bus = 'Unknown'
        try:
            self.vendorid = props['%s.vendor_id' % self.bus]
        except KeyError:
            self.vendorid = None
        try:
            self.deviceid = props['%s.product_id' % self.bus]
        except KeyError:
            self.deviceid = None
        try:
            self.subsysvendorid = props['%s.subsys_vendor_id' % self.bus]
        except KeyError:
            self.subsysvendorid = None
        try:
            self.subsysdeviceid = props['%s.subsys_product_id' % self.bus]
        except KeyError:
            self.subsysdeviceid = None
        try:
            self.description = props['info.product'].strip()
        except KeyError:
            self.description = 'No Description'
        try:
            self.driver = props['info.linux.driver'].strip()
        except KeyError:
            self.driver = 'Unknown'
        self.type = classify_hal(props)
        self.deviceSendString = urlencode({
                            'UUID' :            self.UUID,
                            'Bus' :             self.bus,
                            'Driver' :          self.driver,
                            'Class' :           self.type,
                            'VendorID' :        self.vendorid,
                            'DeviceID' :        self.deviceid,
                            'VendorSubsysID' :  self.subsysvendorid,
                            'DeviceSubsysID' :  self.subsysdeviceid,
                            'Description' :     self.description
                            })

class Host:
    def __init__(self, hostInfo):
        cpuInfo = read_cpuinfo()
        memory = read_memory()
        self.UUID = getUUID()
        self.os = software.read_os()
        self.defaultRunlevel = software.read_runlevel()
        self.bogomips = cpuInfo['bogomips']
        self.cpuVendor = cpuInfo['type']
        self.cpuModel = cpuInfo['model']
        self.numCpus = cpuInfo['count']
        self.cpuSpeed = cpuInfo['speed']
        self.systemMemory = memory['ram']
        self.systemSwap = memory['swap']
        self.kernelVersion = os.uname()[2]
        try:
            self.language = os.environ['LANG']
        except KeyError:
            self.language = 'Unknown'
        try:
            self.platform = hostInfo['system.kernel.machine']
        except KeyError:
            self.platform = 'Unknown'
        try:
            self.systemVendor = hostInfo['system.vendor']
        except:
            try:
                self.systemVendor = cpuInfo['vendor']
            except:
                self.systemVendor = 'Unknown'
        try:
            self.systemModel = hostInfo['system.product']
        except:
            try:
                self.systemModel = cpuInfo['system']
            except:
                self.systemModel = 'Unknown'
        try:
            self.formfactor = hostInfo['system.formfactor']
        except:
            self.formfactor = 'Unknown'

def ignoreDevice(device):
    ignore = 1
    if device.bus == 'Unknown':
        return 1
    if device.bus == 'usb' and device.type == None:
        return 1
    if device.bus == 'usb' and device.driver == 'hub':
        return 1
    if device.bus == 'sound' and device.driver == 'Unknown':
        return 1
    if device.bus == 'pnp' and (device.driver == 'Unknown' or device.driver == 'system'):
        return 1
    return 0

class ServerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def serverMessage(page):
    for line in page.split("\n"):
        if 'ServerMessage:' in line:
            print _('Server Message: "%s"') % line.split('ServerMessage: ')[1]
            if 'Critical' in line:
                raise ServerError, _('Could not contact server: %s') % line.split('ServerMessage: ')[1]


def error(message):
    print >> sys.stderr, message

def debug(message):
    if DEBUG:
        print message

class SystemBusError(Exception):
    def __init__(self, message, hint = None):
        self.message = message
        self.hint = hint

    def __str__(self):
        return str(self.message)
    
class UUIDError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)
    
class Hardware:
    devices = {}
    myDevices = []
    def __init__(self):
        try:
            systemBus = dbus.SystemBus()
        except:
            raise SystemBusError, _('Could not bind to dbus')
        
        mgr = self.dbus_get_interface(systemBus, 'org.freedesktop.Hal', '/org/freedesktop/Hal/Manager', 'org.freedesktop.Hal.Manager')
        try:
            all_dev_lst = mgr.GetAllDevices()
        except:
            raise SystemBusError, _('Could not connect to hal, is it running?'), _('Run "service haldaemon start" as root')

        for udi in all_dev_lst:
            dev = self.dbus_get_interface(systemBus, 'org.freedesktop.Hal', udi, 'org.freedesktop.Hal.Device')
            props = dev.GetAllProperties()
            self.devices[udi] = Device(props)
            if udi == '/org/freedesktop/Hal/devices/computer':
                self.host = Host(props)
        self.hostSendString = urlencode({
                            'UUID' :            self.host.UUID,
                            'OS' :              self.host.os,
                            'defaultRunlevel':  self.host.defaultRunlevel,
                            'language' :        self.host.language,
                            'platform' :        self.host.platform,
                            'bogomips' :        self.host.bogomips,
                            'CPUVendor' :       self.host.cpuVendor,
                            'CPUModel' :        self.host.cpuModel,
                            'numCPUs':          self.host.numCpus,
                            'CPUSpeed' :        self.host.cpuSpeed,
                            'systemMemory' :    self.host.systemMemory,
                            'systemSwap' :      self.host.systemSwap,
                            'vendor' :          self.host.systemVendor,
                            'system' :          self.host.systemModel,
                            'kernelVersion' :   self.host.kernelVersion,
                            'formfactor' :      self.host.formfactor
                            })

    def dbus_get_interface(self, bus, service, object, interface):
        iface = None
        # dbus-python bindings as of version 0.40.0 use new api
        if getattr(dbus, 'version', (0,0,0)) >= (0,40,0):
            # newer api: get_object(), dbus.Interface()
            proxy = bus.get_object(service, object)
            iface = dbus.Interface(proxy, interface)
        else:
            # deprecated api: get_service(), get_object()
            svc = bus.get_service(service)
            iface = svc.get_object(object, interface)
        return iface


    def send(self, user_agent=user_agent, smoonURL=smoonURL, timeout=timeout):
        grabber = urlgrabber.grabber.URLGrabber(user_agent=user_agent, timeout=timeout)
        
        sendHostStr = self.hostSendString
        self.myDevices = []
        for device in self.devices:
            try:
                Bus = self.devices[device].bus
                VendorID = self.devices[device].vendorid
                DeviceID = self.devices[device].deviceid
                SubsysVendorID = self.devices[device].subsysvendorid
                SubsysDeviceID = self.devices[device].subsysdeviceid
                Driver = self.devices[device].driver
                Type = self.devices[device].type
                Description = self.devices[device].description
            except:
                continue
            else:
                if not ignoreDevice(self.devices[device]):
                    self.myDevices.append('%s|%s|%s|%s|%s|%s|%s|%s' % (VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description))
        
        debug('smoon server URL: %s' % smoonURL)
        try:
            token = grabber.urlopen('%s/token?UUID=%s' % (smoonURL, self.host.UUID))
        except urlgrabber.grabber.URLGrabError, e:
            error(_('Error contacting Server: %s') % e)
            return 1
        else:
            for line in token.read().split('\n'):
                if 'tok' in line:
                    tok = line.split(': ')[1]
            token.close()
        
        try:
            tok = tok
        except NameError, e:
            error(_('Communication with server failed'))
            return 1
        
        sendHostStr = sendHostStr + '&token=%s&smoltProtocol=%s' % (tok, smoltProtocol)
        debug('sendHostStr: %s' % self.hostSendString)
        debug('Sending Host')
        
        try:
            o=grabber.urlopen('%s/add' % smoonURL, data=sendHostStr, http_headers=(
                            ('Content-length', '%i' % len(sendHostStr)),
                            ('Content-type', 'application/x-www-form-urlencoded')))
        except urlgrabber.grabber.URLGrabError, e:
            error(_('Error contacting Server: %s') % e)
            return 1
        else:
            serverMessage(o.read())
            o.close()
        
        deviceStr = ''
        for dev in self.myDevices:
            deviceStr = deviceStr + dev + '\n'
        sendDevicesStr = urlencode({'Devices' : deviceStr, 'UUID' : self.host.UUID})
        #debug(sendDevicesStr)
        
        try:
            o=grabber.urlopen('%s/addDevices' % smoonURL, data=sendDevicesStr, http_headers=(
                            ('Content-length', '%i' % len(sendDevicesStr)),
                            ('Content-type', 'application/x-www-form-urlencoded')))
        except urlgrabber.grabber.URLGrabError, e:
            error(_('Error contacting Server: %s') % e)
            return 1
        else:
            serverMessage(o.read())
            o.close()
        return 0
        
    def getProfile(self):
        printBuffer = []

        for label, data in self.hostIter():
            print 
            try:
                printBuffer.append('\t%s: %s' % (label, data))
            except UnicodeDecodeError:
                try:
                    printBuffer.append('\t%s: %s' % (unicode(label, 'utf-8'), data))
                except UnicodeDecodeError:
                    printBuffer.append('\t%r: %r' % (label, data))
            
        printBuffer.append('')
        printBuffer.append('\t\t ' + _('Devices'))
        printBuffer.append('\t\t=================================')
        
        for VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description in self.deviceIter():
            printBuffer.append('\t\t(%s:%s:%s:%s) %s, %s, %s, %s' % (VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description))
            self.myDevices.append('%s|%s|%s|%s|%s|%s|%s|%s' % (VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description))
        return printBuffer


    def hostIter(self):
        '''Iterate over host information.'''
        yield _('UUID'), self.host.UUID
        yield _('OS'), self.host.os
        yield _('Default run level'), self.host.defaultRunlevel
        yield _('Language'), self.host.language
        yield _('Platform'), self.host.platform
        yield _('BogoMIPS'), self.host.bogomips
        yield _('CPU Vendor'), self.host.cpuVendor
        yield _('CPU Model'), self.host.cpuModel
        yield _('Number of CPUs'), self.host.numCpus
        yield _('CPU Speed'), self.host.cpuSpeed
        yield _('System Memory'), self.host.systemMemory
        yield _('System Swap'), self.host.systemSwap
        yield _('Vendor'), self.host.systemVendor
        yield _('System'), self.host.systemModel
        yield _('Form factor'), self.host.formfactor
        yield _('Kernel'), self.host.kernelVersion
        
    def deviceIter(self):
        '''Iterate over our devices.'''
        for device in self.devices:
            try:
                Bus = self.devices[device].bus
                VendorID = self.devices[device].vendorid
                DeviceID = self.devices[device].deviceid
                SubsysVendorID = self.devices[device].subsysvendorid
                SubsysDeviceID = self.devices[device].subsysdeviceid
                Driver = self.devices[device].driver
                Type = self.devices[device].type
                Description = self.devices[device].description
                Description = Description.decode('latin1')
            except:
                continue
            else:
                if not ignoreDevice(self.devices[device]):
                    yield VendorID, DeviceID, SubsysVendorID, SubsysDeviceID, Bus, Driver, Type, Description
                
# From RHN Client Tools

def classify_hal(node):
    # NETWORK
    if node.has_key('net.interface'):
        return 'NETWORK'

    if node.has_key('pci.device_class'):
        if node['pci.device_class'] == PCI_BASE_CLASS_NETWORK:
            return 'NETWORK'

    
    if node.has_key('info.product') and node.has_key('info.category'):
        if node['info.category'] == 'input':
            # KEYBOARD <-- do this before mouse, some keyboards have built-in mice
            if 'keyboard' in node['info.product'].lower():
                return 'KEYBOARD'
            # MOUSE
            if 'mouse' in node['info.product'].lower():
                return 'MOUSE'
    
    if node.has_key('pci.device_class'):
        #VIDEO
        if node['pci.device_class'] == PCI_BASE_CLASS_DISPLAY:
            return 'VIDEO'
        #USB
        if (node['pci.device_class'] ==  PCI_BASE_CLASS_SERIAL
                and node['pci.device_subclass'] == PCI_CLASS_SERIAL_USB):
            return 'USB'
        
        if node['pci.device_class'] == PCI_BASE_CLASS_STORAGE: 
            #IDE
            if node['pci.device_subclass'] == PCI_CLASS_STORAGE_IDE:
                return 'IDE'
            #SCSI
            if node['pci.device_subclass'] == PCI_CLASS_STORAGE_SCSI:
                return 'SCSI'
            #RAID
            if node['pci.device_subclass'] == PCI_CLASS_STORAGE_RAID:
                return 'RAID'
        #MODEM
        if (node['pci.device_class'] == PCI_BASE_CLASS_COMMUNICATION 
                and node['pci.device_subclass'] == PCI_CLASS_COMMUNICATION_MODEM):
            return 'MODEM'
        #SCANNER 
        if (node['pci.device_class'] == PCI_BASE_CLASS_INPUT 
                and node['pci.device_subclass'] == PCI_CLASS_INPUT_SCANNER):
            return 'SCANNER'
        
        if node['pci.device_class'] == PCI_BASE_CLASS_MULTIMEDIA: 
            #CAPTURE -- video capture card
            if node['pci.device_subclass'] == PCI_CLASS_MULTIMEDIA_VIDEO:
                return 'CAPTURE'
            #AUDIO
            if node['pci.device_subclass'] == PCI_CLASS_MULTIMEDIA_AUDIO:
                return 'AUDIO'

        #FIREWIRE
        if (node['pci.device_class'] == PCI_BASE_CLASS_SERIAL 
                and node['pci.device_subclass'] == PCI_CLASS_SERIAL_FIREWIRE):
            return 'FIREWIRE'
        #SOCKET -- PCMCIA yenta socket stuff
        if (node['pci.device_class'] == PCI_BASE_CLASS_BRIDGE 
                and (node['pci.device_subclass'] == PCI_CLASS_BRIDGE_PCMCIA
                or node['pci.device_subclass'] == PCI_CLASS_BRIDGE_CARDBUS)):
            return 'SOCKET'
    
    if node.has_key('storage.drive_type'):
        #CDROM
        if node['storage.drive_type'] == 'cdrom':
            return 'CDROM'
        #HD
        if node['storage.drive_type'] == 'disk':
            return 'HD'
         #FLOPPY
        if node['storage.drive_type'] == 'floppy':
            return 'FLOPPY'
        #TAPE
        if node['storage.drive_type'] == 'tape':
            return 'TAPE'

    #PRINTER
    if node.has_key('printer.product'):
        return 'PRINTER'

    #Catchall for specific devices, only do this after all the others
    if (node.has_key('pci.product_id') or
            node.has_key('usb.product_id')):
        return 'OTHER'

    # No class found
    return None
    
# This has got to be one of the ugliest fucntions alive
def read_cpuinfo():
    def get_entry(a, entry):
        e = entry.lower()
        if not a.has_key(e):
            return ""
        return a[e]

    if not os.access("/proc/cpuinfo", os.R_OK):
        return {}

    cpulist = open("/proc/cpuinfo", "r").read()
    uname = os.uname()[4].lower()
    
    # This thing should return a hwdict that has the following
    # members:
    #
    # class, desc (required to identify the hardware device)
    # count, type, model, model_number, model_ver, model_rev
    # bogomips, platform, speed, cache
    hwdict = { 'class': "CPU",
               "desc" : "Processor",
               }
    if uname[0] == "i" and uname[-2:] == "86" or (uname == "x86_64"):
        # IA32 compatible enough
        count = 0
        tmpdict = {}
        for cpu in cpulist.split("\n\n"):
            if not len(cpu):
                continue
            count = count + 1
            if count > 1:
                continue # just count the rest
            for cpu_attr in cpu.split("\n"):
                if not len(cpu_attr):
                    continue
                vals = cpu_attr.split(':')
                if len(vals) != 2:
                    # XXX: make at least some effort to recover this data...
                    continue
                name, value = vals[0].strip(), vals[1].strip()
                tmpdict[name.lower()] = value

        if uname == "x86_64":
            hwdict['platform'] = 'x86_64'
        else:
            hwdict['platform']      = "i386"
            
        hwdict['count']         = count
        hwdict['type']          = get_entry(tmpdict, 'vendor_id')
        hwdict['model']         = get_entry(tmpdict, 'model name')
        hwdict['model_number']  = get_entry(tmpdict, 'cpu family')
        hwdict['model_ver']     = get_entry(tmpdict, 'model')
        hwdict['model_rev']     = get_entry(tmpdict, 'stepping')
        hwdict['cache']         = get_entry(tmpdict, 'cache size')
        hwdict['bogomips']      = get_entry(tmpdict, 'bogomips')
        hwdict['other']         = get_entry(tmpdict, 'flags')
        mhz_speed               = get_entry(tmpdict, 'cpu mhz')
        if mhz_speed == "":
            # damn, some machines don't report this
            mhz_speed = "-1"
        try:
            hwdict['speed']         = int(round(float(mhz_speed)) - 1)
        except ValueError:
            hwdict['speed'] = -1


    elif uname in["alpha", "alphaev6"]:
        # Treat it as an an Alpha
        tmpdict = {}
        for cpu_attr in cpulist.split("\n"):
            if not len(cpu_attr):
                continue
            vals = cpu_attr.split(':')
            if len(vals) != 2:
                # XXX: make at least some effort to recover this data...
                continue
            name, value = vals[0].strip(), vals[1].strip()
            tmpdict[name.lower()] = value.lower()

        hwdict['platform']      = "alpha"
        hwdict['count']         = get_entry(tmpdict, 'cpus detected')
        hwdict['type']          = get_entry(tmpdict, 'cpu')
        hwdict['model']         = get_entry(tmpdict, 'cpu model')
        hwdict['model_number']  = get_entry(tmpdict, 'cpu variation')
        hwdict['model_version'] = "%s/%s" % (get_entry(tmpdict, 'system type'),
                                             get_entry(tmpdict,'system variation'))
        hwdict['model_rev']     = get_entry(tmpdict, 'cpu revision')
        hwdict['cache']         = "" # pitty the kernel doesn't tell us this.
        hwdict['bogomips']      = get_entry(tmpdict, 'bogomips')
        hwdict['other']         = get_entry(tmpdict, 'platform string')
        hz_speed                = get_entry(tmpdict, 'cycle frequency [Hz]')
        # some funky alphas actually report in the form "462375000 est."
        hz_speed = hz_speed.split()
        try:
            hwdict['speed']         = int(round(float(hz_speed[0]))) / 1000000
        except ValueError:
            hwdict['speed'] = -1

    elif uname in ["ia64"]:
        tmpdict = {}
        count = 0
        for cpu in cpulist.split("\n\n"):
            if not len(cpu):
                continue
            count = count + 1
            # count the rest
            if count > 1:
                continue
            for cpu_attr in cpu.split("\n"):
                if not len(cpu_attr):
                    continue
                vals = cpu_attr.split(":")
                if len(vals) != 2:
                    # XXX: make at least some effort to recover this data...
                    continue
                name, value = vals[0].strip(), vals[1].strip()
                tmpdict[name.lower()] = value.lower()

        hwdict['platform']      = uname
        hwdict['count']         = count
        hwdict['type']          = get_entry(tmpdict, 'vendor')
        hwdict['model']         = get_entry(tmpdict, 'family')
        hwdict['model_ver']     = get_entry(tmpdict, 'archrev')
        hwdict['model_rev']     = get_entry(tmpdict, 'revision')
        hwdict['bogomips']      = get_entry(tmpdict, 'bogomips')
        mhz_speed = tmpdict['cpu mhz']
        try:
            hwdict['speed'] = int(round(float(mhz_speed)) - 1)
        except ValueError:
            hwdict['speed'] = -1
        hwdict['other']         = get_entry(tmpdict, 'features')

    elif uname in ['ppc64','ppc']:
        tmpdict = {}
        count = 0
        for cpu in cpulist.split("\n\n"):
            if not len(cpu):
                continue
            count = count + 1
            # count the rest
            if count > 1:
                continue
            for cpu_attr in cpu.split("\n"):
                if not len(cpu_attr):
                    continue
                vals = cpu_attr.split(":")
                if len(vals) != 2:
                    # XXX: make at least some effort to recover this data...
                    continue
                name, value = vals[0].strip(), vals[1].strip()
                tmpdict[name.lower()] = value.lower()

        hwdict['platform'] = uname
        hwdict['count'] = count
        hwdict['model'] = get_entry(tmpdict, "cpu")
        hwdict['model_ver'] = get_entry(tmpdict, 'revision')
        hwdict['bogomips'] = get_entry(tmpdict, 'bogomips')
        hwdict['vendor'] = get_entry(tmpdict, 'machine')
        hwdict['type'] = get_entry(tmpdict, 'platform')
        hwdict['system'] = get_entry(tmpdict, 'detected as')
        # strings are postpended with "mhz"
        mhz_speed = get_entry(tmpdict, 'clock')[:-3]
        try:
            hwdict['speed'] = int(round(float(mhz_speed)) - 1)
        except ValueError:
            hwdict['speed'] = -1
       
    elif uname in ["sparc64","sparc"]:
        tmpdict = {}
        bogomips = 0
        for cpu in cpulist.split("\n\n"):
            if not len(cpu):
                continue

            for cpu_attr in cpu.split("\n"):
                if not len(cpu_attr):
                    continue
                vals = cpu_attr.split(":")
                if len(vals) != 2:
                    # XXX: make at least some effort to recover this data...
                    continue
                name, value = vals[0].strip(), vals[1].strip()
                if name.endswith('Bogo'): 
                    if bogomips == 0:
                         bogomips = int(round(float(value)) )
                         continue
                    continue
                tmpdict[name.lower()] = value.lower()
        system = ''
        if not os.access("/proc/openprom/banner-name", os.R_OK):
            system = 'Unknown'
        if os.access("/proc/openprom/banner-name", os.R_OK):
            system = open("/proc/openprom/banner-name", "r").read() 
        hwdict['platform'] = uname
        hwdict['count'] = get_entry(tmpdict, 'ncpus probed')
        hwdict['model'] = get_entry(tmpdict, 'cpu')
        hwdict['type'] = get_entry(tmpdict, 'type')
        hwdict['model_ver'] = get_entry(tmpdict, 'type')
        hwdict['bogomips'] = bogomips
        hwdict['vendor'] = 'sun'
        hwdict['cache'] = "" # pitty the kernel doesn't tell us this.
        speed = int(round(float(bogomips))) / 2
        hwdict['speed'] = speed
        hwdict['system'] = system
         
    else:
        # XXX: expand me. Be nice to others
        hwdict['platform']      = uname
        hwdict['count']         = 1 # Good as any
        hwdict['type']          = uname
        hwdict['model']         = uname
        hwdict['model_number']  = ""
        hwdict['model_ver']     = ""
        hwdict['model_rev']     = ""
        hwdict['cache']         = ""
        hwdict['bogomips']      = ""
        hwdict['other']         = ""
        hwdict['speed']         = 0

    # make sure we get the right number here
    if not hwdict["count"]:
        hwdict["count"] = 1
    else:
        try:
            hwdict["count"] = int(hwdict["count"])
        except:
            hwdict["count"] = 1
        else:
            if hwdict["count"] == 0: # we have at least one
                hwdict["count"] = 1

    # If the CPU can do frequency scaling the CPU speed returned
    # by /proc/cpuinfo might be less than the maximum possible for
    # the processor. Check sysfs for the proper file, and if it
    # exists, use that value.  Only use the value from CPU #0 and
    # assume that the rest of the CPUs are the same.
    
    if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq'):
        hwdict['speed'] = int(file('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq').read().strip()) / 1000

    # This whole things hurts a lot.
    return hwdict



def read_memory():
    un = os.uname()
    kernel = un[2]
    if kernel[:3] == "2.6":
        return read_memory_2_6()
    if kernel[:3] == "2.4":
        return read_memory_2_4()

def read_memory_2_4():
    if not os.access("/proc/meminfo", os.R_OK):
        return {}

    meminfo = open("/proc/meminfo", "r").read()
    lines = meminfo.split("\n")
    curline = lines[1]
    memlist = curline.split()
    memdict = {}
    memdict['class'] = "MEMORY"
    megs = int(long(memlist[1])/(1024*1024))
    if megs < 32:
        megs = megs + (4 - (megs % 4))
    else:
        megs = megs + (16 - (megs % 16))
    memdict['ram'] = str(megs)
    curline = lines[2]
    memlist = curline.split()
    # otherwise, it breaks on > ~4gigs of swap
    megs = int(long(memlist[1])/(1024*1024))
    memdict['swap'] = str(megs)
    return memdict

def read_memory_2_6():
    if not os.access("/proc/meminfo", os.R_OK):
        return {}
    meminfo = open("/proc/meminfo", "r").read()
    lines = meminfo.split("\n")
    dict = {}
    for line in lines:
        blobs = line.split(":", 1)
        key = blobs[0]
        if len(blobs) == 1:
            continue
        #print blobs
        value = blobs[1].strip()
        dict[key] = value

    memdict = {}
    memdict["class"] = "MEMORY"

    total_str = dict['MemTotal']
    blips = total_str.split(" ")
    total_k = long(blips[0])
    megs = long(total_k/(1024))

    swap_str = dict['SwapTotal']
    blips = swap_str.split(' ')
    swap_k = long(blips[0])
    swap_megs = long(swap_k/(1024))

    memdict['ram'] = str(megs)
    memdict['swap'] = str(swap_megs)
    return memdict

def getUUID():
    try:
        UUID = file('/etc/sysconfig/hw-uuid').read().strip()
    except IOError:
        try:
            UUID = file('/proc/sys/kernel/random/uuid').read().strip()
            try:
                file('/etc/sysconfig/hw-uuid', 'w').write(self.UUID)
            except:
                sys.stderr.write('Unable to save UUID, continuing...\n')
        except IOError:
            sys.stderr.write('Unable to determine UUID of system!\n')
            raise UUIDError, 'Could not determine UUID of system!\n'
    return UUID
