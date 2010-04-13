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
from cobbler import utils
import ConfigParser

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
    # This removes everything before the first slash.
    path = path[path.find('/'):]
    tree_path_re = re.compile(r'(.*%s)' % path)
    if tree_path_re.search(kerneldir):
        tree_path = tree_path_re.search(kerneldir).group(1)

    # if not importing an nfs tree we get things wrong
    if tree.find("nfs://") == -1:
        path = tree_path
        path = path[path.find('/')+1:]
        path = path[path.find('/')+1:]
        path = path[path.find('/'):]

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
        return distro

    repo_path_re = re.compile(r'(%s.*)/repodata' % paths['path'])
    tree_repos = None

    if rcm is not None:
        distro_path = paths['path']
        while distro_path != '':
            distro_path = '/'.join(distro_path.split('/')[1:])
            prepos = None
            try:
                prepos = rcm.tree_repos(distro_path)
                break
            except xmlrpclib.ResponseError:
                pass
        if prepos:
            repos = []
            for prepo in prepos:
                repo = os.path.join(paths['tree_path'],prepos[prepo],"repodata")
                if os.path.exists(repo) and repo_path_re.search(repo):
                    repos.append('beaker-%s,%s' % (prepo, repo_path_re.search(repo).group(1)))
            tree_repos = ':'.join(repos)
             
    # Catch Fedora Repos
    repo = os.path.join(paths['tree_path'],"repodata")
    if not tree_repos and os.path.exists(repo):
        if repo_path_re.search(repo):
            tree_repos = repo_path_re.search(repo).group(1)

    if not tree_repos:
        # Catch RHEL5 Repos
        try:
            repos = glob.glob(os.path.join(paths['tree_path'],"*/repodata"))
            if repos:
                for i, repo in enumerate(repos):
                    if repo_path_re.search(repos[i]):
                        repos[i] = repo_path_re.search(repos[i]).group(1)
        except TypeError:
            return distro
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
        return distro
    distro['ks_meta']['tree_repos'] = tree_repos
    cobbler.modify_distro(distro['id'],'ksmeta',distro['ks_meta'],token)
    return distro

def update_comment(distro):
    paths = get_paths(distro)

    if not paths:
        return distro
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
        return distro
    filename = data2[0]
    cpio_object = tempfile.TemporaryFile()
    try:
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
        cpio_object.close()
    except rpmUtils.RpmUtilsError, e:
        print "Warning, %s" % e
    if os.path.exists("%s/../../.composeinfo" % paths['tree_path']):
        parser = ConfigParser.ConfigParser()
        parser.read("%s/../../.composeinfo" % paths['tree_path'])
        try:
            distro['comment'] = "%s\narches=%s" % (distro['comment'], parser.get('tree','arches'))
        except ConfigParser.NoSectionError:
            print "missing section tree in %s/../../.composeinfo" % paths['tree_path']
    if os.path.exists("%s/.treeinfo" % paths['tree_path']):
        parser = ConfigParser.ConfigParser()
        parser.read("%s/.treeinfo" % paths['tree_path'])
        try:
            family  = parser.get('general','family').replace(" ","")
        except ConfigParser.NoSectionError:
            print "missing section general in %s/.treeinfo" % paths['tree_path']
        except ConfigParser.NoOptionError:
            print "missing option family in %s/.treeinfo" % paths['tree_path']
        try:
            version = parser.get('general', 'version').replace("-",".")
        except ConfigParser.NoSectionError:
            print "missing section general in %s/.treeinfo" % paths['tree_path']
        except ConfigParser.NoOptionError:
            print "missing option version in %s/.treeinfo" % paths['tree_path']
        try:
            distro['comment'] = "%s\nvariant=%s" % (distro['comment'],
                                                    parser.get('general', 'variant'))
        except ConfigParser.NoSectionError:
            print "missing section general in %s/.treeinfo" % paths['tree_path']
        except ConfigParser.NoOptionError:
            print "missing option variant in %s/.treeinfo" % paths['tree_path']
        family = "%s%s" % ( family, version.split('.')[0] )
        if version.find('.') != -1:
            update = version.split('.')[1]
    elif os.path.exists("%s/.discinfo" % paths['tree_path']):
        discinfo = open("%s/.discinfo" % paths['tree_path'], "r")
        familyupdate = discinfo.read().split("\n")[1]
        family = familyupdate.split(".")[0].replace(" ","")
        if familyupdate.find('.') != -1:
            update = familyupdate.split(".")[1].replace(" ","")
        discinfo.close()
        
    distro['comment'] = "%s\nfamily=%s.%s" % (distro['comment'], family, update)
    cobbler.modify_distro(distro['id'],'comment',distro['comment'],token)
    kickstart = findKickstart(distro['arch'], family, update)
    if kickstart:
        profile_id = cobbler.get_profile_handle(distro['name'],token)
        cobbler.modify_profile(profile_id,'kickstart',kickstart,token)
        cobbler.save_profile(profile_id,token)
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
    cobbler = xmlrpclib.ServerProxy('http://127.0.0.1/cobbler_api')
    token = cobbler.login("", utils.get_shared_secret())
    settings = cobbler.get_settings(token)
    rcm = None
    if 'rcm' in settings:
        rcm = xmlrpclib.ServerProxy(settings['rcm'])

    distros = cobbler.get_distros()
    push_distros = []

    for distro in distros:
        # If we haven't pushed this distro to Inventory yet, then its the first
        # time importing it, look for repos and specific family.
        if distro['comment'].find("PUSHED") == -1:
            distro['id'] = cobbler.get_distro_handle(distro['name'],token)
            print "Update TreeRepos for %s" % distro['name']
            distro = update_repos(distro)
            print "Update Family for %s" % distro['name']
            distro = update_comment(distro)
            push_distros.append(distro)
    if push_distros:
        inventory = xmlrpclib.ServerProxy('%s/RPC2' % settings['redhat_management_server'], allow_none=True)
        distros = inventory.labcontrollers.addDistros(settings['server'], push_distros)
        for distro in push_distros:
            comment = "%s\nPUSHED" % distro['comment']
            cobbler.modify_distro(distro['id'],'comment',comment,token)
            cobbler.save_distro(distro['id'],token)
        # Needed for legacy RHTS
        addDistroCmd = '/var/lib/beaker/addDistro.sh'
        if os.path.exists(addDistroCmd):
            valid_variants = ['AS', 'ES', 'WS', 'Desktop']
            release = re.compile(r'family=([^\s]+)')
            variant_search = re.compile(r'variant=([^\s]+)')
            for distro in push_distros:
                # Only process nfs distros and skip xen distros too
                if distro['name'].find('_nfs-') == -1 or \
                   distro['name'].find('-xen-') != -1:
                    continue
                VARIANT=''
                FAMILYUPDATE=None
                DISTPATH='nightly'
                if 'tree' in distro['ks_meta']:
                    if distro['ks_meta']['tree'].find('/rel-eng/') != -1:
                        DISTPATH='rel-eng'
                    if distro['ks_meta']['tree'].find('/released/') != -1:
                        DISTPATH='released'
                DIST=distro['name'].split('_')[0]
                meta = string.join(distro['name'].split('_')[1:],'_').split('-')
                for curr_variant in valid_variants:
                    if curr_variant in meta:
                        VARIANT = curr_variant
                        break
                TPATH = DISTPATH + ''.join(distro['ks_meta']['tree'].split(DISTPATH,1)[1:])
                if release.search(distro['comment']):
                    FAMILYUPDATE=release.search(distro['comment']).group(1)
                if variant_search.search(distro['comment']):
                    VARIANT = variant_search.search(distro['comment']).group(1)
                #addDistro.sh rel-eng RHEL6.0-20090626.2 RedHatEnterpriseLinux6.0 x86_64 Default rel-eng/RHEL6.0-20090626.2/6/x86_64/os
                if FAMILYUPDATE:
                    cmd = '%s %s %s %s %s "%s" %s' % (addDistroCmd, DISTPATH, DIST,
                                                    FAMILYUPDATE, distro['arch'],
                                                    VARIANT, TPATH)
                    print cmd
                    os.system(cmd)

