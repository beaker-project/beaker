
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

from bkr.common import __version__
from bkr.log import log_to_stream
from bkr.server.model import OSMajor
from bkr.server.util import load_config_or_exit, run_createrepo
from optparse import OptionParser
from turbogears.config import get
import os
import sys
import urlparse
import dnf
import urllib
import requests
import logging

__description__ = 'Script to update harness repos'

USAGE_TEXT = """ Usage: repo_update """

log = logging.getLogger(__name__)

def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option("--baseurl", "-b",
                      default="https://beaker-project.org/yum/harness/",
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

# Use a single global requests.Session for this process
# for connection pooling.
requests_session = requests.Session()

# We distinguish this particular situation from other errors which may occur
# while fetching packages, because it's "expected" in some cases -- for example
# Atomic Host or RHVH which can be imported into Beaker, but cannot have
# harness packages and thus there will be no corresponding directory to
# download from.
class HarnessRepoNotFoundError(ValueError): pass

class RPMPayloadLocation(dnf.repo.RPMPayload):
    def __init__(self, pkg, progress, pkg_location):
        super(RPMPayloadLocation, self).__init__(pkg, progress)
        self.package_dir = os.path.dirname(pkg_location)

    def _target_params(self):
        tp = super(RPMPayloadLocation, self)._target_params()
        dnf.util.ensure_dir(self.package_dir)
        tp['dest'] = self.package_dir
        return tp

# This is a cutdown version of reposync.
class RepoSyncer(dnf.Base):

    def __init__(self, repo_url, output_dir):
        super(RepoSyncer, self).__init__()
        repo_id = repo_url.replace('/', '-')
        self.repos.add_new_repo(repo_id, self.conf, baseurl=[repo_url])
        self.repo_url = repo_url
        self.output_dir = output_dir

    # Verify the remote package's checksum against the local copy
    def verify_checksum(self, package, dest_path):
        (chksum_type, chksum) = package.returnIdSum()
        real_sum = dnf.yum.misc.checksum(chksum_type, dest_path,
                                         datasize=package._size)
        return real_sum == chksum

    def sync(self):
        # First check if the harness repo exists.
        response = requests_session.head(urlparse.urljoin(self.repo_url, 'repodata/repomd.xml'))
        if response.status_code != 200:
            raise HarnessRepoNotFoundError()

        log.info('Syncing packages from %s to %s', self.repo_url, self.output_dir)
        self.fill_sack(load_system_repo=False)
        pkglist = self.sack.query().latest().filterm(arch__neq='src')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        remote_pkgs, _ = self._select_remote_pkgs(pkglist)
        new_packages = []
        for package in remote_pkgs:
            dest = os.path.join(self.output_dir, os.path.basename(package.relativepath))
            if os.path.exists(dest):
                if self.verify_checksum(package, dest):
                    log.info('Skipping %s', dest)
                    continue
                else:
                    log.info('Unlinking bad package %s', dest)
                    os.unlink(dest)
            new_packages.append(package)
            log.info('Fetching %s', os.path.join(self.output_dir, package.relativepath))

        if new_packages:
            progress = dnf.callback.NullDownloadProgress()
            drpm = dnf.drpm.DeltaInfo(self.sack.query().latest(), progress, 0)
            payloads = [RPMPayloadLocation(package, progress, os.path.join(self.output_dir, os.path.basename(package.relativepath)))
                        for package in new_packages]
            self._download_remote_payloads(payloads, drpm, progress, None)  # pylint: disable=no-member
            flag_path = os.path.join(self.output_dir, '.new_files')
            with open(flag_path, 'wb'):
                os.utime(flag_path, None)

def update_repos(baseurl, basepath):
    # We only sync repos for the OS majors that have existing trees in the lab controllers.
    for osmajor in OSMajor.in_any_lab():
        # urlgrabber < 3.9.1 doesn't handle unicode urls
        osmajor = unicode(osmajor).encode('utf8')
        dest = "%s/%s" % (basepath,osmajor)
        if os.path.islink(dest):
            continue # skip symlinks
        syncer = RepoSyncer(urlparse.urljoin(baseurl, '%s/' % urllib.quote(osmajor)), dest)
        try:
            syncer.sync()
        except KeyboardInterrupt:
            raise
        except HarnessRepoNotFoundError:
            log.warning('Harness packages not found for OS major %s, ignoring', osmajor)
            continue
        flag_path = os.path.join(dest, '.new_files')
        if os.path.exists(flag_path):
            createrepo_results = run_createrepo(cwd=dest)
            returncode = createrepo_results.returncode
            if returncode != 0:
                err = createrepo_results.err
                command = createrepo_results.command
                raise RuntimeError('Createrepo failed.\nreturncode:%s cmd:%s err:%s'
                        % (returncode, command, err))
            os.unlink(flag_path)


def main():
    parser = get_parser()
    opts,args = parser.parse_args()
    configfile = opts.configfile
    baseurl = opts.baseurl
    # The base URL is always a directory with a trailing slash
    if not baseurl.endswith('/'):
        baseurl += '/'
    load_config_or_exit(configfile)
    log_to_stream(sys.stderr, level=logging.DEBUG if opts.debug else logging.WARNING)
    if opts.basepath:
        basepath = opts.basepath
    else:
        basepath = get("basepath.harness")
    sys.exit(update_repos(baseurl=baseurl, basepath=basepath))

if __name__ == '__main__':
    main()
