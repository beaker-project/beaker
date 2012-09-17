#!/usr/bin/python

__requires__ = ['TurboGears']

from bkr.server.model import OSMajor
from bkr.server.util import load_config, log_to_stream
from optparse import OptionParser
from turbogears.database import session
from turbogears.config import get
from sqlalchemy.exc import InvalidRequestError, IntegrityError
import os
import sys
import traceback
import urlparse
import shutil
import yum, yum.misc, yum.packages
import urllib

__version__ = '0.1'
__description__ = 'Script to update harness repos'

USAGE_TEXT = """ Usage: repo_update """


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option("--baseurl", "-b",
                      default="http://beaker-project.org/yum/harness/",
                      help="This should be url location of the repos")
    parser.add_option("--basepath", "-d",
                      default=None,
                      help="Optionally specify the harness dest.")
    parser.add_option("-c","--config-file",dest="configfile",default=None)
    return parser


def usage():
    print USAGE_TEXT
    sys.exit(-1)

# Can't use /usr/bin/reposync for this, because it tries to replicate the 
# ../../ in rpm paths and generally makes a mess of things.
# This is a cutdown version of reposync.
class RepoSyncer(yum.YumBase):

    def __init__(self, repo_url, output_dir):
        super(RepoSyncer, self).__init__()
        self.doConfigSetup(init_plugins=False)
        cachedir = yum.misc.getCacheDir()
        assert cachedir is not None # ugh
        self.repos.setCacheDir(cachedir)
        self.conf.cachedir = cachedir
        self.repos.disableRepo('*')
        repo_id = repo_url.replace('/', '-')
        self.add_enable_repo(repo_id, baseurls=[repo_url])
        self.output_dir = output_dir

        # yum foolishness: http://lists.baseurl.org/pipermail/yum-devel/2010-June/007168.html
        yum.packages.base = None

    def sync(self):
        self.doRepoSetup()
        # have to list every possible arch here, ughhhh
        self.doSackSetup(archlist='noarch i386 i686 x86_64 ia64 ppc ppc64 s390 s390x'.split())
        repo, = self.repos.listEnabled()
        package_sack = yum.packageSack.ListPackageSack(
                self.pkgSack.returnPackages(repoid=repo.id))
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        for package in package_sack.returnNewestByNameArch():
            dest = os.path.join(self.output_dir, os.path.basename(package.relativepath))
            if os.path.exists(dest) and os.path.getsize(dest) == package.size:
                print 'Skipping %s' % dest
                continue
            print 'Fetching %s' % dest
            package.localpath = dest
            cached_package = repo.getPackage(package)
            # Based on some confusing cache configuration, yum may or may not 
            # have fetched the package to the right place for us already
            if os.path.exists(dest) and os.path.samefile(cached_package, dest):
                continue
            shutil.copy2(cached_package, dest)

def update_repos(baseurl, basepath):
    for osmajor in OSMajor.query:
        # urlgrabber < 3.9.1 doesn't handle unicode urls
        osmajor = unicode(osmajor).encode('utf8')
        dest = "%s/%s" % (basepath,osmajor)
        syncer = RepoSyncer(urlparse.urljoin(baseurl, '%s/' % urllib.quote(osmajor)), dest)
        try:
            syncer.sync()
        except KeyboardInterrupt:
            raise
        except Exception, e:
            print >>sys.stderr, str(e)
            continue
        cmd = "pushd %s && createrepo -q --checksum sha ." % dest
        print cmd
        os.system(cmd)

def main():
    parser = get_parser()
    opts,args = parser.parse_args()
    configfile = opts.configfile
    baseurl = opts.baseurl
    load_config(configfile)
    log_to_stream(sys.stderr)
    if opts.basepath:
        basepath = opts.basepath
    else:
        basepath = get("basepath.harness", "/var/www/beaker/harness")
    update_repos(baseurl=baseurl, basepath=basepath)

if __name__ == '__main__':
    main()
