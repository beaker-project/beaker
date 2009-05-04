#!/usr/bin/python

import sys, os, rpm
import rpmUtils.transaction
import gzip
import tempfile
import re
import glob
import xmlrpclib
import cpioarchive
import string
import cobbler.api as capi
from ConfigParser import ConfigParser

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
 
def get_paths(distro):
    signatures = [
       'RedHat/RPMS',
       'RedHat/rpms',
       'RedHat/Base',
       'Fedora/RPMS',
       'Fedora/rpms',
       'CentOS/RPMS',
       'CentOS/rpms',
       'CentOS'     ,
       'Packages'   ,
       'Fedora'     ,
       'Server'     ,
       'Client'     ,
    ]

    kerneldir = distro.kernel
    if 'tree' in distro.ks_meta:
        tree   = distro.ks_meta['tree']
    else:
        return None
    path = tree
    while True:
        if kerneldir.find(path) != -1:
            break
        else:
            path = path[1:]
    tree_path_re = re.compile(r'(.*%s)' % path)
    if tree_path_re.search(kerneldir):
        tree_path = tree_path_re.search(kerneldir).group(1)

    found = None
    while kerneldir != os.path.dirname(tree_path):
        for x in signatures:
            d = os.path.join( kerneldir, x)
            if os.path.exists( d ):
                found = True
                break
        if found:
            break
        kerneldir = os.path.dirname(kerneldir)

    return dict( tree_path = tree_path, 
                      path = path,
              package_path = os.path.join(tree_path ,x))

def update_repos(distro):
    paths = get_paths(distro)

    if not paths:
        return False
    repo_path_re = re.compile(r'(%s.*)/repodata' % paths['path'])
    tree_repos = None
    repo = os.path.join(paths['tree_path'],"repodata")
    # Catch Fedora Repos
    if os.path.exists(repo):
        if repo_path_re.search(repo):
            tree_repos = repo_path_re.search(repo).group(1)
    else:
        # Catch RHEL5 Repos
        try:
            repos = glob.glob(os.path.join(paths['tree_path'],"*/repodata"))
            if repos:
                for i, repo in enumerate(repos):
                    if repo_path_re.search(repos[i]):
                        repos[i] = repo_path_re.search(repos[i]).group(1)
        except TypeError:
            return False
        tree_repos = string.join(repos,':')

    if not tree_repos:
        # Look for RHEL4/3 Repos
        arch_variant_re = re.compile(r'[^-]+-([^-/]+)/*$')
        if arch_variant_re.search(paths['tree_path']):
            variant = arch_variant_re.search(paths['tree_path']).group(1)
            repo = os.path.join(paths['tree_path'], "../repo-%s/repodata" % variant)
            if os.path.exists(repo):
                if repo_path_re.search(repo):
                    tree_repos = repo_path_re.search(repo).group(1)
        variant_arch_re = re.compile(r'([^/]+)/([^/]+)/tree$')
        if variant_arch_re.search(paths['tree_path']):
            variant = variant_arch_re.search(paths['tree_path']).group(1)
            arch = variant_arch_re.search(paths['tree_path']).group(2)
            repo = os.path.join(paths['tree_path'], "../repo-%s-%s/repodata" % (variant,arch))
            if os.path.exists(repo):
                if repo_path_re.search(repo):
                    tree_repos = repo_path_re.search(repo).group(1)

    if not tree_repos:
        return False
    ks_meta = distro.ks_meta
    ks_meta['tree_repos'] = tree_repos
    distro.set_ksmeta(ks_meta)
    bootapi.add_distro(distro)
    return distro

def update_comment(distro):
    paths = get_paths(distro)

    if not paths:
        return False
    family = ""
    update = 0
    data = glob.glob(os.path.join(paths['package_path'], "*release-*"))
    data2 = []
    for x in data:
        b = os.path.basename(x)
        if b.find("fedora") != -1 or \
           b.find("redhat") != -1 or \
           b.find("centos") != -1:
            data2.append(x)
    if not data2:
        return False
    filename = data2[0]
    cpio_object = tempfile.TemporaryFile()
    rpm2cpio(filename,cpio_object)
    cpio_object.seek(0)
    cpio = cpioarchive.CpioArchive(fileobj=cpio_object)
    for entry in cpio:
        if entry.name == './etc/fedora-release':
            release = entry.read().split('\n')[0]
            releaseregex = re.compile(r'(.*)\srelease\s(\d+).(\d*)')
            if releaseregex.search(release):
                family = "%s%s" % (releaseregex.search(release).group(1),
                                   releaseregex.search(release).group(2))
                if releaseregex.search(release).group(3):
                    update = releaseregex.search(release).group(3)
                else:
                    update = 0
        if entry.name == './etc/redhat-release':
            release = entry.read().split('\n')[0]
            updateregex = re.compile(r'Update\s(\d+)')
            releaseregex = re.compile(r'release\s\d+.(\d+)')
            if updateregex.search(release):
                update = updateregex.search(release).group(1)
            if releaseregex.search(release):
                update = releaseregex.search(release).group(1)
    if os.path.exists("%s/.treeinfo" % paths['tree_path']):
        parser = ConfigParser()
        parser.read("%s/.treeinfo" % paths['tree_path'])
        try:
            family  = parser.get('general','family').replace(" ","")
        except ConfigParser.NoSectionError:
            pass
        try:
            version = parser.get('general', 'version').replace("-",".")
        except ConfigParser.NoSectionError:
            pass
        family = "%s%s" % ( family, version.split('.')[0] )
        if version.find('.') != -1:
            update = version.split('.')[1]
    elif os.path.exists("%s/.discinfo" % paths['tree_path']):
        update = 0
        discinfo = open("%s/.discinfo" % paths['tree_path'], "r")
        familyupdate = discinfo.read().split("\n")[1]
        family = familyupdate.split(".")[0].replace(" ","")
        if familyupdate.find('.') != -1:
            update = familyupdate.split(".")[1].replace(" ","")
        discinfo.close()
        
    comment = "%s\nfamily=%s.%s" % (distro.comment, family, update)
    distro.set_comment(comment)
    bootapi.add_distro(distro)
    kickstart = findKickstart(distro.arch, family, update)
    if kickstart:
        profile = bootapi.find_profile(distro.name)
        profile.set_kickstart(kickstart)
        bootapi.add_profile(profile)
    return distro

def findKickstart(arch, family, update):
    kickbase = "/var/lib/cobbler/kickstarts"
    flavor = family.strip('0123456789')
    kickstarts = [
           "%s/%s/%s.%s.ks" % (kickbase,arch,family,update),
           "%s/%s/%s.ks" % (kickbase,arch,family),
           "%s/%s/%s.ks" % (kickbase,arch,flavor),
           "%s/%s.%s.ks" % (kickbase,family,update),
           "%s/%s.ks" % (kickbase,family),
           "%s/%s.ks" % (kickbase,flavor),
           "%s/%s/default.ks" % (kickbase,arch),
           "%s/%s.ks" % (kickbase,family),
    ]
    for kickstart in kickstarts:
        if os.path.exists(kickstart):
            return kickstart
    return None

if __name__ == '__main__':
    bootapi = capi.BootAPI()
    settings = bootapi.settings()

    distros = bootapi.distros()
    push_distros = []

    for distro in distros:
        update = False
        if 'tree_repos' not in distro.ks_meta:
            print "Update TreeRepos for %s" % distro.name
            tmpdistro = update_repos(distro)
            if tmpdistro:
                distro = tmpdistro
                update = True
        if distro.comment.find("family=") == -1:
            print "Update Family for %s" % distro.name
            tmpdistro = update_comment(distro)
            if tmpdistro:
                distro = tmpdistro
                update = True
        if update:
            push_distros.append(distro.to_datastruct())
    if push_distros:
        inventory = xmlrpclib.ServerProxy('%s/RPC2' % settings.redhat_management_server, allow_none=True)
        distros = inventory.labcontrollers.addDistros(settings.server, 
                                                         push_distros)
