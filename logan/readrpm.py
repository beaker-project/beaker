#!/usr/bin/python

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
