#!/usr/bin/python
__requires__ = ['TurboGears']

import sys
import errno
import shutil
import datetime
import urlparse
import requests, requests.auth
from bkr import __version__ as bkr_version
from optparse import OptionParser
from bkr.server.model import Job
from bkr.server.util import load_config, log_to_stream
from turbogears.database import session
import logging

logger = logging.getLogger(__name__)

__description__ = 'Script to delete expired log files'

def main():

    parser = OptionParser('usage: %prog [options]',
            description='Permanently deletes log files from Beaker and/or '
                'archive server',
            version=bkr_version)
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
    options, args = parser.parse_args()
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
        requests_session = requests.session(
                auth=requests.auth.HTTPKerberosAuth(require_mutual_auth=False))
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
            session.close()
            logger.exception('Exception while deleting logs for %s', job.t_id)
            failed = True
            continue
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
