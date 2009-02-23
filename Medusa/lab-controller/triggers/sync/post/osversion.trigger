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

    kerneldir = distro['kernel']
    if 'tree' in distro['ks_meta']:
        tree   = distro['ks_meta']['tree']
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
    distro_id = remote.get_distro_handle(distro['name'],token)
    ks_meta = distro['ks_meta']
    ks_meta['tree_repos'] = tree_repos
    remote.modify_distro(distro_id,'ksmeta', ks_meta, token)
    return remote.save_distro(distro_id, token)

def update_comment(distro):
    paths = get_paths(distro)

    if not paths:
        return False
    family = ""
    update = 0
    if os.path.exists("%s/.discinfo" % paths['tree_path']):
        discinfo = open("%s/.discinfo" % paths['tree_path'], "r")
        family = discinfo.read().split("\n")[1].split(".")[0].replace(" ","")
        discinfo.close()
    data = glob.glob(os.path.join(paths['package_path'], "*release-*"))
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
    distro_id = remote.get_distro_handle(distro['name'],token)
    comment = "%s\nfamily=%s.%s" % (distro['comment'], family, update)
    remote.modify_distro(distro_id,'comment', comment, token)
    return remote.save_distro(distro_id, token)

if __name__ == '__main__':
    url = "http://localhost:25152"
    remote = xmlrpclib.ServerProxy(url,allow_none=True)

    token = remote.login("testing","testing")

    remote.update(token)

    distros = remote.get_distros_since(0.0)

    for distro in distros:
        if 'tree_repos' not in distro['ks_meta']:
            print "Update TreeRepos for %s" % distro['name']
            if update_repos(distro):
                print "Sucess"
            else:
                print "Fail"
        if distro['comment'].find("family=") == -1:
            print "Update Family for %s" % distro['name']
            if update_comment(distro):
                print "Success"
            else:
                print "Fail"
