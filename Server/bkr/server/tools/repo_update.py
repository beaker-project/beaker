#!/usr/bin/python
from bkr.server.model import OSMajor
from bkr.server.util import load_config
from optparse import OptionParser
from turbogears.database import session
from turbogears.config import get
from sqlalchemy.exceptions import InvalidRequestError, IntegrityError
import tempfile
import os

__version__ = '0.1'
__description__ = 'Script to update harness repos'

USAGE_TEXT = """ Usage: repo_update """


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,version=__version__)
    parser.add_option("--baseurl", "-b",
                      default="http://repos.fedorapeople.org/repos/beaker/beaker", 
                      help="This should be url location of the repos")
    parser.add_option("--basepath", "-d",
                      default=None,
                      help="Optionally specify the harness dest.")
    parser.add_option("--reposync", "-r",
                      default=None,
                      help="Optionally specify the reposync args.")
    parser.add_option("-c","--config-file",dest="configfile",default=None)
    return parser


def usage():
    print USAGE_TEXT
    sys.exit(-1)

def update_repos(baseurl, basepath, rflags):
    for osmajor in OSMajor.query():
        for arch in osmajor.osversion[0].arches:
            repoarch = arch
            # pick up i686 packages
            if arch.arch == 'i386':
                repoarch = 'i686'
            fd, fn = tempfile.mkstemp(prefix="bkr_repo", suffix="")
            repoid = os.path.basename(fn)
            tfile = os.fdopen(fd, 'w')
            tfile.write("[%s]\n" % arch)
            tfile.write("name=%s\n" % arch)
            tfile.write("baseurl=%s/%s/%s\n" % (baseurl, osmajor, arch))
            tfile.write("gpgcheck=0\n")
            tfile.close()
            dest = "%s/%s" % (basepath,osmajor)
            cmd = "/usr/bin/reposync %s --config=%s \
                                        --repoid=%s \
                                        --arch=%s \
                                        --download_path=%s" % (rflags, 
                                                               fn,
                                                               arch,
                                                               repoarch,
                                                               dest)
            print cmd
            os.system(cmd)
            os.unlink(fn)
            cmd = "pushd %s/%s && createrepo -q ." % (dest, arch)
            print cmd
            os.system(cmd)

def main():
    parser = get_parser()
    opts,args = parser.parse_args()
    configfile = opts.configfile
    baseurl = opts.baseurl
    rflags = opts.reposync
    load_config(configfile)
    if opts.basepath:
        basepath = opts.basepath
    else:
        basepath = get("basepath.harness", "/var/www/beaker/harness")
    update_repos(baseurl=baseurl, basepath=basepath, rflags=rflags)

if __name__ == '__main__':
    main()
