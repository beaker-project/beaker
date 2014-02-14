#!/usr/bin/python

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

from bkr.log import log_to_stream
from bkr.server.model import OSMajor
from bkr.server.util import load_config, run_createrepo
from optparse import OptionParser
from turbogears.config import get
import os
import sys
import urlparse
import shutil
import yum, yum.misc, yum.packages
import urllib
import logging

__version__ = '0.1'
__description__ = 'Script to update harness repos'

USAGE_TEXT = """ Usage: repo_update """

log = logging.getLogger(__name__)

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
    parser.add_option('--debug', action='store_true',
            help='Show detailed progress information')
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
        self.repo_url = repo_url
        self.output_dir = output_dir

        # yum foolishness: http://lists.baseurl.org/pipermail/yum-devel/2010-June/007168.html
        yum.packages.base = None

    def sync(self):
        has_new_packages = False
        log.info('Syncing packages from %s to %s', self.repo_url, self.output_dir)
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
                log.info('Skipping %s', dest)
                continue
            log.info('Fetching %s', dest)
            package.localpath = dest
            cached_package = repo.getPackage(package)
            has_new_packages = True
            # Based on some confusing cache configuration, yum may or may not 
            # have fetched the package to the right place for us already
            if os.path.exists(dest) and os.path.samefile(cached_package, dest):
                continue
            shutil.copy2(cached_package, dest)
        return has_new_packages

def update_repos(baseurl, basepath):
    for osmajor in OSMajor.query:
        # urlgrabber < 3.9.1 doesn't handle unicode urls
        osmajor = unicode(osmajor).encode('utf8')
        dest = "%s/%s" % (basepath,osmajor)
        syncer = RepoSyncer(urlparse.urljoin(baseurl, '%s/' % urllib.quote(osmajor)), dest)
        try:
            has_new_packages = syncer.sync()
        except KeyboardInterrupt:
            raise
        except Exception, e:
            log.warning('%s', e)
            continue
        if has_new_packages:
            createrepo_results = run_createrepo(cwd=dest)
            returncode = createrepo_results.returncode
            if returncode != 0:
                err = createrepo_results.err
                command = createrepo_results.command
                raise RuntimeError('Createrepo failed.\nreturncode:%s cmd:%s err:%s'
                     % (returncode, command, err))


def main():
    parser = get_parser()
    opts,args = parser.parse_args()
    configfile = opts.configfile
    baseurl = opts.baseurl
    load_config(configfile)
    log_to_stream(sys.stderr, level=logging.DEBUG if opts.debug else logging.WARNING)
    if opts.basepath:
        basepath = opts.basepath
    else:
        basepath = get("basepath.harness", "/var/www/beaker/harness")
    sys.exit(update_repos(baseurl=baseurl, basepath=basepath))

if __name__ == '__main__':
    main()
