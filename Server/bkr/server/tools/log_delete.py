#!/usr/bin/python

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
import errno
import shutil
import urlparse
import warnings
import requests
from turbogears import config
from bkr.common import __version__
from bkr.log import log_to_stream
from optparse import OptionParser
from bkr.server.model import Job
from bkr.server.util import load_config
from turbogears.database import session
import logging

try:
    import requests_kerberos
    import kerberos
    _kerberos_available = True
except ImportError:
    _kerberos_available = False

logger = logging.getLogger(__name__)
warnings.filterwarnings('always', 'Use beaker-log-delete instead', DeprecationWarning)

__description__ = 'Script to delete expired log files'


class MultipleAuth(requests.auth.AuthBase):

    def __init__(self, auths, *args, **kwargs):
        super(MultipleAuth, self).__init__(*args, **kwargs)
        self.auths = auths

    def __call__(self, request):
        for auth in self.auths:
            request = auth(request)
        return request


def legacy_main(argv=None):
    warnings.warn("Use beaker-log-delete instead", DeprecationWarning)
    return main(argv)

def main(argv=None):

    parser = OptionParser('usage: %prog [options]',
            description='Permanently deletes log files from Beaker and/or '
                'archive server',
            version=__version__)
    parser.add_option('-c', '--config', metavar='FILENAME',
            help='Read configuration from FILENAME')
    parser.add_option('-v', '--verbose', action='store_true',
            help='Print the path/URL of deleted files to stdout')
    parser.add_option('--debug', action='store_true',
            help='Print debugging messages to stderr')
    parser.add_option('--dry-run', action='store_true',
            help='Do not delete any files, and issue ROLLBACK instead of '
                'COMMIT after performing database operations')
    parser.add_option('--limit', default=None, type='int',
        help='Set a limit on the number of jobs whose logs will be deleted')
    parser.set_defaults(verbose=False, debug=False, dry_run=False)
    options, args = parser.parse_args(argv)
    load_config(options.config)
    # urllib3 installs a NullHandler, we can just remove it and let the messages propagate
    logging.getLogger('requests.packages.urllib3').handlers[:] = []
    log_to_stream(sys.stderr, level=logging.DEBUG if options.debug else logging.WARNING)
    return log_delete(options.verbose, options.dry_run, options.limit)

def log_delete(print_logs=False, dry=False, limit=None):
    if dry:
        logger.info('Dry run only')
    logger.info('Getting expired jobs')

    failed = False
    if not dry:
        requests_session = requests.Session()
        log_delete_user = config.get('beaker.log_delete_user')
        log_delete_password = config.get('beaker.log_delete_password')

        available_auths = []
        available_auth_names = []

        if _kerberos_available:
            available_auths.append(requests_kerberos.HTTPKerberosAuth(
                mutual_authentication=requests_kerberos.DISABLED))
            available_auth_names.append('Kerberos')

        if log_delete_user and log_delete_password:
            available_auths.append(requests.auth.HTTPDigestAuth(log_delete_user,
                log_delete_password))
            available_auth_names.append('HTTPDigestAuth')
        requests_session.auth = MultipleAuth(available_auths)
        logger.debug('Available authentication methods: %s' %
            ', '.join(available_auth_names))

    for job, logs in Job.expired_logs(limit):
        logger.info('Deleting logs for %s', job.t_id)
        try:
            session.begin()
            for log in logs:
                if not dry:
                    if urlparse.urlparse(log).scheme:
                        response = requests_session.delete(log)
                        if response.status_code not in (200, 204, 404):
                            response.raise_for_status()
                    else:
                        try:
                            shutil.rmtree(log)
                        except OSError, e:
                            if e.errno == errno.ENOENT:
                                pass
                if print_logs:
                    print log
            if not dry:
                job.delete()
                session.commit()
                session.close()
            else:
                session.close()
        except Exception, e:
            logger.exception('Exception while deleting logs for %s', job.t_id)
            failed = True
            # session needs to be open for job.t_id in the log message above
            session.close()
            continue
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
