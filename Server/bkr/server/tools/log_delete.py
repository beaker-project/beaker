import errno, shutil, datetime
from bkr import __version__ as bkr_version
from optparse import OptionParser
from bkr.server.model import Job
from turbogears.database import session
from bkr.common.dav import BeakerRequest, DavDeleteErrorHandler, RedirectHandler
import urllib2 as u2
from urllib2_kerberos import HTTPKerberosAuthHandler


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
    log_delete(options.verbose, options.dry_run, options.config)



def log_delete(verb=False, dry=False, config=None):
    from bkr.server.util import load_config
    load_config(config)
    job_logs = Job.expired_logs()
    # The only way to override default HTTPRedirectHandler
    # is to pass it into build_opener(). Appending does not work
    opener = u2.build_opener(RedirectHandler()) 
    opener.add_handler(HTTPKerberosAuthHandler())
    opener.add_handler(DavDeleteErrorHandler())
    if dry:
        print 'Dry run only'
    for job_log in job_logs:
        job = job_log[0]
        logs = job_log[1]
        try:
            session.begin()
            job.deleted = datetime.datetime.utcnow()
            for log in logs:
                if not dry:
                    if 'http' in log:
                        url = log
                        req = BeakerRequest('DELETE', url=url)
                        opener.open(req)
                    else:
                        try:
                            shutil.rmtree(log)
                        except OSError, e:
                            if e.errno == errno.ENOENT:
                                pass
                if verb:
                    print log

        except Exception:
            session.rollback()
            raise
        else:
            if not dry:
                session.commit()
            else:
                session.rollback()

if __name__ == '__main__':
    main()

