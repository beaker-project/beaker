#!/usr/bin/python

from ctypes import *

class PedCHSGeometry(Structure):
    _fields_ = [("cylinders", c_int), ("heads", c_int), ("sectors", c_int)]

class PedDevice(Structure):
    pass
PedDevice._fields_ = [("next", POINTER(PedDevice)),
                      ("model", c_char_p),
                      ("path", c_char_p),
                      ("type", c_int),
                      ("sector_size", c_longlong),
                      ("phys_sector_size", c_longlong),
                      ("length", c_longlong),
                      ("open_count", c_int),
                      ("read_only", c_int),
                      ("external_mode", c_int),
                      ("dirty", c_int),
                      ("boot_dirty", c_int),
                      ("hw_geom", PedCHSGeometry),
                      ("bios_geom", PedCHSGeometry),
                      ("host", c_short),
                      ("did", c_short),
                      ("arch_specific", c_void_p),
                     ]

class Disk(object):
    def __init__(self, disk):
        self.length = disk.length
        self.size = disk.length * disk.sector_size
        self.sector_size = disk.sector_size
        self.phys_sector_size = disk.phys_sector_size
        self.model = disk.model

    def to_dict(self):
        # need to send size as an XML-RPC string as it is likely to overflow
        # the 32-bit size limit for XML-RPC ints
        return dict( size = str(self.size),
                     sector_size = self.sector_size,
                     phys_sector_size = self.phys_sector_size,
                     model = self.model)

class Disks(object):
    def __init__(self):
        """
        """
        self.disks = []

        try:
            parted = CDLL("libparted-1.8.so.0")
        except:
            try: 
                parted = CDLL("libparted-2.1.so.0")
            except:
                parted = CDLL("libparted.so.0")

        parted.ped_device_get_next.restype = POINTER(PedDevice)
        parted.ped_device_probe_all(None)

        disk = None
        try:
            while True:
                disk = parted.ped_device_get_next(disk)
                if disk[0].type in [1, 2, 6, 9, 15] and "/dev/sr" not in disk[0].path:
                    self.disks.append(Disk(disk[0]))
        except ValueError:
            pass

    def __iter__(self):
            return self.disks.__iter__()

    def nr_disks(self):
        return len(self.disks)

    nr_disks = property(nr_disks)

    def disk_space(self):
        diskspace = 0
        for disk in self.disks:
            diskspace += disk.size
        return diskspace

    disk_space = property(disk_space)

if __name__ == '__main__':
    disks = Disks()
    for disk in disks:
        print disk.to_dict()
    print disks.nr_disks
    print disks.disk_space
