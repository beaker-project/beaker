#!/usr/bin/python

import sys, os, rpm
import time
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
import getopt

class MyConfigParser(object):
    def __init__(self, config):
        self.parser = None
        if os.path.exists(config):
            self.parser = ConfigParser.ConfigParser()
            try:
                self.parser.read(config)
            except ConfigParser.MissingSectionHeaderError, e:
                self.parser = None
                print e
                
    def get(self, section, key, default=''):
        if self.parser:
            try:
                default = self.parser.get(section, key)
            except (ConfigParser.NoSectionError,ConfigParser.NoOptionError), e:
                print e
        return default

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
        return 

    repo_path_re = re.compile(r'(%s.*)/repodata' % paths['path'])
    tree_repos = []

    # If rcm is defined we can ask what repos are defined for this tree
    if rcm is not None:
        distro_path = paths['path']
        prepos = []
        while distro_path != '':
            distro_path = '/'.join(distro_path.split('/')[1:])
            if not distro_path:
                break
            try:
                prepos = rcm.tree_repos(distro_path)
                break
            except xmlrpclib.ResponseError:
                pass
        for prepo in prepos:
            repo = os.path.join(paths['tree_path'],prepos[prepo],"repodata")
            if os.path.exists(repo) and repo_path_re.search(repo):
                tree_repos.append('beaker-%s,%s' % (
                                         prepo, 
                                         repo_path_re.search(repo).group(1),
                                                   )
                                 )
    # rcm is not avaialble, fall back to glob...
    else:
        variant_arch_re = re.compile(r'([^/]+)/([^/]+)/tree$')
        if variant_arch_re.search(paths['tree_path']):
            variant = variant_arch_re.search(paths['tree_path']).group(1)
        else:
            variant = ''
        tree_repos = ['beaker-%s,%s' % 
                             (os.path.basename(os.path.dirname(repo)),
                              repo_path_re.search(repo).group(1),
                             ) for repo in \
                     glob.glob(os.path.join(paths['tree_path'],
                                   "*/repodata")
                              ) + \
                     glob.glob(os.path.join(paths['tree_path'], 
                                   "../repo-*%s*/repodata" % variant)
                              ) + \
                     glob.glob(os.path.join(paths['tree_path'], 
                                   "../debug*/repodata")
                              )
                     ]

    if tree_repos:
        distro['ks_meta']['tree_repos'] = ':'.join(tree_repos)
        cobbler.modify_distro(distro['id'],'ksmeta',distro['ks_meta'],token)
    return


def read_data(distro):
    # If data={} exists in comment field eval it "safely"
    # This allows for caching and for overriding values we would
    # get from here.
    comment_search = re.compile(r'(data=({.*}))')
    search = comment_search.search(distro['comment'])
    if search:
        results = search.group(1)
        try:
            data = eval(search.group(2),{},{})
            # Remove data=... from comment in case parts are updated
            distro['comment'] = '%s' % distro['comment'].replace(search.group(1),'')
            distro['keys'] = set(data.keys())
            for key in list(distro['keys']):
                distro[key] = data[key]
        except SyntaxError:
            pass
    # If its the first time we won't have a pushed entry..
    if 'pushed' not in distro:
        distro['pushed'] = False
        if 'keys' not in distro:
            distro['keys'] = set()
        distro['keys'].add('pushed')
    return distro

def update_comment(distro):
    paths = get_paths(distro)
    if not paths:
        return distro
    family = ""
    update = 0
    myparser = MyConfigParser("%s/../../.composeinfo" % paths['tree_path'])
    # Use the name of the tree from .composeinfo if it exists.
    distro['treename'] = distro.get('treename') or \
                                     myparser.get('tree','name', 
                                     distro['name'].split('_')[0])
    distro['keys'].add('treename')

    distro['arches'] = distro.get('arches') or \
                                  map(string.strip, 
                                  myparser.get('tree','arches').split(','))
    distro['keys'].add('arches')

    myparser = MyConfigParser("%s/.treeinfo" % paths['tree_path'])
    if myparser.parser:
        labels = myparser.get('general','label')
        distro['tags'] = distro.get('tags') or \
                                     map(string.strip,
                                     labels and labels.split(',') or [])
        distro['keys'].add('tags')
        family  = myparser.get('general','family').replace(" ","")
        version = myparser.get('general', 'version').replace("-",".")
        distro['variant'] = distro.get('variant') or \
                                        myparser.get('general', 'variant')
        distro['keys'].add('variant')
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
    else:
        data = glob.glob(os.path.join(paths['package_path'], "*release-*"))
        data2 = []
        for x in data:
            b = os.path.basename(x)
            if b.find("fedora") != -1 or \
               b.find("redhat") != -1 or \
               b.find("centos") != -1:
                data2.append(x)
        if data2:
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
                            family = "%s%s" % (
                                           releaseregex.search(release).group(1),
                                           releaseregex.search(release).group(2)
                                              )
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

    distro['osmajor'] = distro.get('osmajor') or family
    distro['keys'].add('osmajor')
    distro['osminor'] = distro.get('osminor') or update
    distro['keys'].add('osminor')
    kickstart = findKickstart(distro['arch'], 
                              distro.get('osmajor'),
                              distro.get('osminor')
                             )

    if kickstart:
        profile_id = cobbler.get_profile_handle(distro['name'],token)
        cobbler.modify_profile(profile_id,'kickstart',kickstart,token)
        cobbler.save_profile(profile_id,token)
    return distro

def save_data(distro):
    data = dict()
    for key in list(distro['keys']):
        data[key] = distro[key]
    comments = '%sdata=%s' % (distro['comment'], data)
    cobbler.modify_distro(distro['id'],'comment',comments, token)
    cobbler.save_distro(distro['id'],token)

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
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f")
        force = False
        for o, a in opts:
            if o == '-f':
                force = True
    except:
        print str(err)
        usage()
        sys.exit(2)


    new_run = time.time()
    cobbler = xmlrpclib.ServerProxy('http://127.0.0.1/cobbler_api')
    token = cobbler.login("", utils.get_shared_secret())
    settings = cobbler.get_settings(token)
    rcm = None
    if 'rcm' in settings:
        rcm = xmlrpclib.ServerProxy(settings['rcm'])

    filename="/var/run/beaker-lab-controller/osversion.mtime" 
    if os.path.exists(filename) and not force:
        last_run = float(open(filename).readline())
    else:
        last_run = 0.0

    distros = cobbler.get_distros_since(last_run)
    proxy = xmlrpclib.ServerProxy('http://localhost:8000', 
                                   allow_none=True)

    for distro in distros:
        distro = read_data(distro)
        # If we haven't pushed this distro to Inventory yet, then its the first
        # time importing it, look for repos and specific family.
        if distro['pushed'] == False or force:
            distro['id'] = cobbler.get_distro_handle(distro['name'],token)
            print "Update Family for %s" % distro['name']
            distro = update_comment(distro)

            # Add the distro to inventory only if treename exists
            if distro.get('treename'):

                # Skip xen Distros
                if distro.get('name').find('-xen-') != -1:
                    print "Skipping Xen distro %s" % distro.get('name')
                    continue

                print "Update TreeRepos for %s" % distro['name']
                update_repos(distro)

                # xmlrpc can't marshal set
                distro['keys'] = list(distro['keys'])

                proxy.addDistro(distro)

                # Kick off jobs automatically
                addDistroCmd = '/var/lib/beaker/addDistro.sh'
                if os.path.exists(addDistroCmd) and \
                   distro.get('ks_meta').get('tree') and \
                   distro.get('osmajor') and \
                   distro.get('osminor'):
                   #addDistro.sh "rel-eng" RHEL6.0-20090626.2 RedHatEnterpriseLinux6.0 x86_64 "Default"
                        cmd = '%s "%s" %s %s %s "%s"' % (addDistroCmd, 
                                                       ','.join(distro.get('tags',[])),
                                                       distro.get('treename'),
                                                       '%s.%s' % (
                                                         distro.get('osmajor'), 
                                                         distro.get('osminor')),
                                                       distro.get('arch'),
                                                       distro.get('variant',''))
                        print cmd
                        os.system(cmd)

                # Record in cobbler that we PUSHED it
                distro['pushed'] = True
                save_data(distro)
        else:
            print "Already pushed %s, set comment pushed True to False to re-push" % distro['name']

    FH = open(filename, "w")
    FH.write('%s' % new_run)
    FH.close()
