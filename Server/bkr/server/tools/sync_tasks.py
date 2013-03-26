#!/usr/bin/env python

DESCRIPTION = """ beaker-sync-tasks is a script to sync task RPMs between
two Beaker instances
"""

__doc__ = """

beaker-sync-tasks: Tool to sync Beaker task RPMs between two Beaker instances
=============================================================================

Synopsis
--------

`beaker-sync-tasks` [*options*]

Description
-----------

beaker-sync-tasks is a script to sync tasks between two Beaker instances.

Syncing protocol:

- Task doesn't exist in destination: copy it.
- Task exists in destination: Overwrite it, if it is a different version
  on the source
- Tasks which exist on the destination and not on the source are left
  untouched

Options
-------

-h, --help                                   show this help message and exit

Source and destination:
  -s SOURCE, --source=SOURCE                   Source Beaker Instance
  -d DESTINATION, --destination=DESTINATION    Destination Beaker Instance

Credentials:
  -u USERNAME, --username=USERNAME             Username for the destination server
  -p PASSWORD, --password=PASSWORD             Password for the destination server
  -k, --kerberos                               Specify to use Kerberos authentication

Extra:
  --krb_realm=KRB_REALM                        Specify Kerberos realm
  --krb_service=KRB_SERVICE                    Specify Kerberos service
  --force                                      Do not ask before overwriting task RPMs

Examples
--------

Using Kerberos authentication:

$ beaker-sync-tasks --source=http://127.0.0.1/bkr --destination=http://my-remote-beaker --kerberos

Using Username/password:

$ beaker-sync-tasks --source=http://127.0.0.1/bkr --destination=http://my-remote-beaker --username <username>
Password:

$ beaker-sync-tasks --source=http://127.0.0.1/bkr --destination=http://my-remote-beaker --username <username> --password <mypass>

Don't prompt before beginning task upload:

$ beaker-sync-tasks --source=http://127.0.0.1/bkr --destination=http://my-remote-beaker --kerberos --force

"""
import os
import sys
import xmlrpclib
import lxml.etree as ET
import urllib2
import logging
from multiprocessing.pool import ThreadPool
from urllib2 import urlopen
from urlparse import urljoin
from optparse import OptionParser
import getpass

# We need kobo
try:
    import kobo.xmlrpc
    from kobo.client import HubProxy
except ImportError:
    print 'Please install kobo client library'
    sys.exit(1)

__description__ = 'Script to sync tasks between two Beaker instances'
__version__ = '0.1'


# Helper function which doesn't need to be a class method
def find_task_version_url(task_xml):

    xml = ET.fromstring(task_xml)
    return xml.find('.').attrib['version'], \
        xml.find('./rpms/rpm').attrib['url']

class TaskLibrarySync:

    def __init__(self, source, dest, kobo_conf):

        self.source = source
        self.dest = dest
        self.kobo_conf = kobo_conf
        source_proxy = self._get_server_proxy(self.source)
        dest_proxy = self._get_server_proxy(self.dest)
        self.proxy={'source':source_proxy,
                    'dest':dest_proxy
                    }

        # detect invalid credentials early
        self.check_login()

    def _get_server_proxy(self, server):

        kobo_conf = self.kobo_conf.copy()
        kobo_conf['HUB_URL'] = server
        hub = HubProxy(kobo_conf)

        return hub

    def check_login(self):

        # we can continue if the credentials are not valid for source, since
        # we do not need correct credentials if we are not uploading tasks
        if not self.proxy['dest']._logged_in:
            logging.info('Invalid credentials for %s. Cannot Continue.' %self.dest)
            sys.exit(1)

    def get_tasks(self, server):

        tasks = self.proxy[server].tasks.filter({'valid':1})
        return [task['name'] for task in tasks]

    def _get_task_xml(self, task):

        # This is being executed as part of a thread pool and xmlrpclib
        # is not thread safe. Hence we create a new proxy object.
        proxy = self._get_server_proxy(self.source)
        try:
            return proxy.tasks.to_xml(task, False)
        except xmlrpclib.Fault:
            # If something goes wrong with this task, for example:
            # https://bugzilla.redhat.com/show_bug.cgi?id=915549
            # we do our best to continue anyway...
            return None

    def tasks_diff(self,new_tasks, old_tasks):

        pool = ThreadPool(processes=4)
        task_xml = pool.map(self._get_task_xml, new_tasks)

        task_urls = []
        for xml in task_xml:
            if xml:
                task_urls.append(find_task_version_url(xml)[1])

        for task in old_tasks:
            task_xml = self.proxy['source'].tasks.to_xml(task, False)
            source_task_version, source_task_url = find_task_version_url(task_xml)

            task_xml = self.proxy['dest'].tasks.to_xml(task, False)
            dest_task_version = find_task_version_url(task_xml)[0]

            if source_task_version != dest_task_version:
                task_urls.append(source_task_url)

        return task_urls

    def _upload(self, task_url):

        task_rpm_name = os.path.split(task_url)[1]
        try:
            task_rpm_data = urlopen(task_url).read()
        except urllib2.HTTPError as e:
            logging.critical('Error retrieving %s' %task_rpm_name)
        else:
            # Upload
            try:
                logging.info('Uploading task %s' %task_rpm_name)
                # This is being executed as part of a thread pool and xmlrpclib
                # is not thread safe. Hence we create a new proxy object.
                proxy = self._get_server_proxy(self.dest)
                proxy.tasks.upload(task_rpm_name, \
                                                    xmlrpclib.Binary(task_rpm_data))
            except xmlrpclib.Fault, e:
                logging.critical('Error uploading task: %s' % e.faultString)

        return

    def tasks_upload(self, task_urls):

        pool = ThreadPool(processes=4)
        # fire upload
        pool.map(self._upload, task_urls)

        # Serial
        for url in task_urls:
            self._upload(url)

        return

def get_parser():

    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__, version=__version__)

    parser.add_option('-s', '--source', dest='source',
                      help='Source Beaker Instance',
                     metavar='SOURCE')
    parser.add_option('-d', '--destination', dest='destination',
                      help='Destination Beaker Instance',
                      metavar='DESTINATION')
    parser.add_option('-u', '--username', dest='username',
                      help='Username for the destination server',
                      metavar='USERNAME')
    parser.add_option('-p', '--password', dest='password', default=None,
                      help='Password for the destination server',
                      metavar='PASSWORD')
    parser.add_option('-k', '--kerberos', action='store_true',dest='kerberos',
                      help='Specify to use Kerberos authentication')

    parser.add_option('--krb_realm', dest='krb_realm',
                      help='Specify Kerberos realm')

    parser.add_option('--krb_service', dest='krb_service',
                      help='Specify Kerberos service')

    parser.add_option('--force', action='store_true',dest='force',default=False,
                      help='Do not ask before overwriting task RPMs')



    return parser

def setup(options):

    kobo_conf = {}

    if options.username and options.password:
        kobo_conf['AUTH_METHOD'] = 'password'
        kobo_conf['USERNAME'] = options.username
        kobo_conf['PASSWORD'] = options.password

    if options.kerberos:
        kobo_conf['AUTH_METHOD'] = 'krbv'

        if options.krb_service:
            kobo_conf['KRB_SERVICE'] = options.krb_service
        if options.krb_realm:
            kobo_conf['KRB_REALM'] = options.krb_realm

    if options.username and options.password and options.kerberos:
        logging.info('You have specified both username/password and Kerberos, Kerberos will be used')

    source = options.source.rstrip('/')
    destination = options.destination.rstrip('/')

    return source, destination, kobo_conf

def main():

    parser = get_parser()
    (options, args) = parser.parse_args()

    # Sanity check
    if None in [options.source, options.destination]:
        logging.info('Please specify both source and destination Beaker instances')
        parser.print_help()
        sys.exit(1)

    if None in [options.username,options.password] and not options.kerberos:
        if options.password is None:
            options.password = getpass.getpass()
        else:
            logging.info('Please specify either an username/password or enable kerberos authentication')
            parser.print_help()
            sys.exit(1)

    # Setup logging
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger = logging.getLogger('')
    logger.addHandler(stdout_handler)
    logger.setLevel(logging.INFO)

    # setup source, destination hubs, etc.
    source, dest, kobo_conf = setup(options)
    task_sync = TaskLibrarySync(source, dest, kobo_conf)

    # Get list of tasks from source and destination
    logging.info('Getting the list of tasks from source and destination..')
    source_tasks = task_sync.get_tasks('source')
    dest_tasks = task_sync.get_tasks('dest')

    # new_tasks -> Tasks which do not exist on the destination
    # old_tasks-> Tasks which exist on source and destination
    new_tasks = list(set(source_tasks).difference(dest_tasks))
    old_tasks = list(set(source_tasks).intersection(dest_tasks))

    # Get the task URL's to upload to destination
    logging.info('Finding tasks to upload to destination..')
    task_urls = task_sync.tasks_diff(new_tasks, old_tasks)

    # Upload
    if len(task_urls) > 0:
        logging.warning('Warning: Tasks already present in %s will be overwritten with the version from %s.' %  \
                            (task_sync.source, task_sync.dest))

        if not options.force:
            proceed = raw_input('Proceed? (y/n) ')
            if proceed.lower() == 'y':
                proceed = True
        else:
            proceed = True

        if proceed:
            logging.info('Starting upload of %d tasks..'% len(task_urls))
            task_sync.tasks_upload(task_urls)
        else:
            logging.info('Task syncing aborted.')

    else:
        logging.info('No tasks to be uploaded to destination from source')

    return

# Begin here
if __name__ == '__main__':
    main()
