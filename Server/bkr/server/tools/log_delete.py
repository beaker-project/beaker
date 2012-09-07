
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
            description='Permanently deletes log files from Beaker and/or \
                archive server',
            version=bkr_version)
    parser.add_option('-c', '--config', metavar='FILENAME',
            help='Read configuration from FILENAME')
    parser.add_option('-v', '--verbose', action='store_true',
            help='Return deleted files')
    parser.add_option('--dry-run', action='store_true',
            help='Execute deletions, but issue ROLLBACK instead of COMMIT, \
                and do not actually delete files')
    parser.set_defaults(verbose=False, dry_run=False)
    options, args = parser.parse_args()
    load_config(options.config)
    log_to_stream(sys.stderr)
    log_delete(options.verbose, options.dry_run)

def log_delete(verb=False, dry=False):
    if dry:
        print 'Dry run only'
    if verb:
        print 'Getting expired jobs'

    if not dry:
        requests_session = requests.session(
                auth=requests.auth.HTTPKerberosAuth(require_mutual_auth=False))
    for job, logs in Job.expired_logs():
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
                if verb:
                    print log
            if not dry:
                job.delete()
                session.commit()
                session.close()
            else:
                session.close()
        except Exception, e:
            session.close()
            logger.error(str(e))
            continue

if __name__ == '__main__':
    main()

