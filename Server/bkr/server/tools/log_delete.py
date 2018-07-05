
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['TurboGears']

import sys
import os, os.path
import errno
import datetime
import shutil
import urlparse
import warnings
import requests
from turbogears import config
from sqlalchemy.sql import and_
from bkr.common import __version__
from bkr.log import log_to_stream
from optparse import OptionParser
from bkr.server.model import Job
from bkr.server.util import load_config_or_exit
from turbogears.database import session
import logging

try:
    import requests_kerberos
    import kerberos
    _kerberos_available = True
except ImportError:
    _kerberos_available = False

logger = logging.getLogger(__name__)


def remove_descendants(paths):
    """
    Given a list of URLs (or filesystem paths) to directories we want to 
    delete, for example:
        http://server/a/
        http://server/a/x/
        http://server/a/y/
        http://server/b/
        ...
    this function filters out any paths which have a common prefix with an 
    earlier item in the list, and returns what's left. In this example:
        http://server/a/
        http://server/b/
        ...

    This is necessary because if we first delete the subtree under 
        http://server/a/
    we cannot then delete the subtree under
        http://server/a/x/
    because it's already gone.
    """
    previous = None
    for path in sorted(paths):
        if previous is None or not path.startswith(previous):
            previous = path
            yield path

class MultipleAuth(requests.auth.AuthBase):

    def __init__(self, auths, *args, **kwargs):
        super(MultipleAuth, self).__init__(*args, **kwargs)
        self.auths = auths

    def __call__(self, request):
        for auth in self.auths:
            request = auth(request)
        return request


def main(argv=None):

    parser = OptionParser('usage: %prog [options]',
            description='Deletes expired jobs and permanently purges log files '
                        'from Beaker and/or archive server',
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
    load_config_or_exit(options.config)

    # urllib3 installs a NullHandler, we can just remove it and let the messages propagate
    logging.getLogger('requests.packages.urllib3').handlers[:] = []
    log_to_stream(sys.stderr, level=logging.DEBUG if options.debug else logging.WARNING)
    return log_delete(options.verbose, options.dry_run, options.limit)

def log_delete(print_logs=False, dry=False, limit=None):
    if dry:
        logger.info('Dry run only')

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

    logger.info('Fetching expired jobs to be deleted')
    try:
        session.begin()
        for job in Job.query.filter(Job.is_expired).limit(limit):
            logger.info('Deleting expired job %s', job.id)
            job.deleted = datetime.datetime.utcnow()
        if not dry:
            session.commit()
        else:
            session.rollback()
        session.close()
    except Exception as e:
        logger.exception('Exception while deleting expired jobs')
        failed = True
        session.close()

    logger.info('Fetching deleted jobs to be purged')
    with session.begin():
        jobs = Job.query.filter(and_(Job.is_deleted, Job.purged == None)).limit(limit)
        job_ids = [job_id for job_id, in jobs.values(Job.id)]
    for jobid in job_ids:
        logger.info('Purging logs for deleted job %s', jobid)
        try:
            session.begin()
            job = Job.by_id(jobid)
            all_logs = job.all_logs(load_parent=False)
            # We always delete entire directories, not individual log files, 
            # because that's faster, and because we never mix unrelated log 
            # files together in the same directory so it's safe to do that.
            # We keep a trailing slash on the directories otherwise when we try 
            # to DELETE them, Apache will first redirect us to the trailing 
            # slash.
            log_dirs = (os.path.dirname(log.full_path) + '/' for log in all_logs)
            for path in remove_descendants(log_dirs):
                if not dry:
                    if urlparse.urlparse(path).scheme:
                        # We need to handle redirects ourselves, since requests
                        # turns DELETE into GET on 302 which we do not want.
                        response = requests_session.delete(path, allow_redirects=False)
                        redirect_limit = 10
                        while redirect_limit > 0 and response.status_code in (
                                301, 302, 303, 307):
                            response = requests_session.delete(
                                    response.headers['Location'],
                                    allow_redirects=False)
                            redirect_limit -= 1
                        if response.status_code not in (200, 204, 404):
                            response.raise_for_status()
                    else:
                        try:
                            shutil.rmtree(path)
                        except OSError, e:
                            if e.errno == errno.ENOENT:
                                pass
                if print_logs:
                    print path
            job.purge()
            if not dry:
                session.commit()
            else:
                session.rollback()
            session.close()
        except Exception, e:
            logger.exception('Exception while purging logs for job %s', jobid)
            failed = True
            session.close()
            continue
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
