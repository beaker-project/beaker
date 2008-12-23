#!/usr/bin/python

import sys, os, rpm
import rpmUtils.transaction
import gzip
import tempfile
import re
import glob
from cobbler import api
from cobbler import action_import
import cobbler
sys.path.append("/var/www/labcontroller")
import cpioarchive


def rpm2cpio(rpm_file, out=sys.stdout, bufsize=2048):
    """Performs roughly the equivalent of rpm2cpio(8).
       Reads the package from fdno, and dumps the cpio payload to out,
       using bufsize as the buffer size."""
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    fdno = os.open(rpm_file, os.O_RDONLY)
    hdr = ts.hdrFromFdno(fdno)
    del ts
    compr = hdr[rpm.RPMTAG_PAYLOADCOMPRESSOR] or 'gzip'
    #if compr == 'bzip2':
        # TODO: someone implement me!
    #el
    if compr != 'gzip':
        raise rpmUtils.RpmUtilsError, \
              'Unsupported payload compressor: "%s"' % compr
    f = gzip.GzipFile(None, 'rb', None, os.fdopen(fdno, 'rb', bufsize))
    while 1:
        tmp = f.read(bufsize)
        if tmp == "": break
        out.write(tmp)
    f.close()
                                                                                                                              
def update_comment(distro):
    distro_path = os.path.join("/", *distro.kernel.split("/")[:-3])
    try:
        breed, rootdir = action_import.guess_breed(distro.kernel, distro_path)
    except cobbler.cexceptions.CX:
        return False
    family = ""
    update = 0
    if os.path.exists("%s/.discinfo" % rootdir[0]):
        discinfo = open("%s/.discinfo" % rootdir[0], "r")
        family = discinfo.read().split("\n")[1].split(".")[0].replace(" ","")
        discinfo.close()
    data = glob.glob(os.path.join(rootdir[0],rootdir[1], "*release-*"))
    data2 = []
    for x in data:
        if x.find("generic") == -1:
            data2.append(x)
    if not data2:
        return False
    filename = data2[0]
    cpio_object = tempfile.TemporaryFile()
    rpm2cpio(filename,cpio_object)
    cpio_object.seek(0)
    cpio = cpioarchive.CpioArchive(fileobj=cpio_object)
    for entry in cpio:
        if entry.name == './etc/redhat-release':
            release = entry.read().split('\n')[0]
            updateregex = re.compile(r'Update\s(\d+)')
            releaseregex = re.compile(r'release\s\d+.(\d+)')
            if updateregex.search(release):
                update = updateregex.search(release).group(1)
            if releaseregex.search(release):
                update = releaseregex.search(release).group(1)
    comment = distro.comment
    distro.set_comment("%s\nfamily=%s.%s" % (comment,family,update))
    return distros.add(distro,save=True,with_triggers=False)

if __name__ == '__main__':
    cobbler_api = api.BootAPI()
    distros = cobbler_api.distros()
    for distro in distros:
        if distro.comment.find("family=") == -1:
            print "Update %s" % distro.name
            if update_comment(distro):
                print "Success"
            else:
                print "Fail"
