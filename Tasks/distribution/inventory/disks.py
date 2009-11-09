#!/usr/bin/python

import sys
sys.path.append("/usr/lib/anaconda")
import isys
import parted

class Disks(object):
    def __init__(self):
        """
        """
        self.disks = []
        for disk in isys.hardDriveDict().keys():
            self.disks.append(int("%d" % self.disksize(
                                     parted.device_get("/dev/%s" % disk))))

    def disksize(self, disk):
        return (float(disk.heads * disk.cylinders * disk.sectors) 
                             / ( 1024 * 1024) * disk.sector_size)
    def nr_disks(self):
        return len(self.disks)

    nr_disks = property(nr_disks)

    def diskspace(self):
        diskspace = 0
        for disk in self.disks:
            diskspace += disk
        return diskspace

    diskspace = property(diskspace)

if __name__ == '__main__':
    disks = Disks()
    print disks.nr_disks
    print disks.disks
    print disks.diskspace
