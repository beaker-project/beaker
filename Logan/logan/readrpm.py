#!/usr/bin/python

# Logan - Logan is the scheduling piece of the Beaker project
#
# Copyright (C) 2008 bpeck@redhat.com
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys, os, rpm
from subprocess import *
                                                                                                                               
def get_rpm_info(rpm_file):
    """Returns rpm information by querying a rpm"""
    ts = rpm.ts()
    fdno = os.open(rpm_file, os.O_RDONLY)
    try:
        hdr = ts.hdrFromFdno(fdno)
    except rpm.error:
        fdno = os.open(rpm_file, os.O_RDONLY)
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
        hdr = ts.hdrFromFdno(fdno)
    os.close(fdno)
    return { 'name': hdr[rpm.RPMTAG_NAME], 'ver' : "%s-%s" % (hdr[rpm.RPMTAG_VERSION],\
    hdr[rpm.RPMTAG_RELEASE]), 'epoch': hdr[rpm.RPMTAG_EPOCH],\
    'arch': hdr[rpm.RPMTAG_ARCH] , 'files': hdr['filenames']}
                                                                                                                               
if __name__ == '__main__':
    blob = sys.argv[1]
    rpm_info = get_rpm_info(blob)
    print "name:%s" % rpm_info['name']
    print "version:%s" % rpm_info['ver']
    print "arch:%s" % rpm_info['arch']
    for file in rpm_info['files']:
        if file.endswith('testinfo.desc'):
            p1 = Popen(["rpm2cpio", blob], stdout=PIPE)
            p2 = Popen(["cpio", "--extract" , "--to-stdout", ".%s" % file], stdin=p1.stdout, stdout=PIPE)
            print p2.communicate()[0]
