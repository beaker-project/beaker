#!/usr/bin/env python

__requires__=['TurboGears']

DESCRIPTION = """ beaker-sync-tasks is a script to sync local Beaker Task RPMs from a remote
Beaker installation
"""
__doc__ = """

beaker-sync-tasks: Tool to sync local Beaker task RPMs from a remote Beaker installation
========================================================================================

Synopsis
--------

`beaker-sync-tasks` [*options*]

Description
-----------

beaker-sync-tasks is a script to sync local task RPMs from a remote Beaker installation

Syncing protocol:

- Task doesn't exist in local: copy it.
- Task exists in local: Overwrite it, if it is a different version
  on the remote
- Tasks which exist on the local and not on the remote are left
  untouched

Options
-------

-h, --help                                     show this help message and exit

Servers:
  --remote=REMOTE                              Remote Beaker instance

Extra:
  --force                                      Do not ask before overwriting task RPMs
  --debug                                      Display messages useful for debugging (verbose)

Examples
--------

Sync tasks from a remote Beaker server and display debug messages:

$ beaker-sync-tasks --remote=http://127.0.0.1/bkr --debug

Don't prompt before beginning task upload:

$ beaker-sync-tasks --remote=http://127.0.0.1/bkr --force

More information
----------------

Querying the existing tasks: The script communicates with the remote Beaker server via XML-RPC
calls and directly interacts with the local Beaker database.

Adding new tasks: The tasks to be added to the local Beaker database
are first downloaded in the task directory (usually,
/var/www/beaker/rpms). Each of these tasks are then added to the
Beaker database and finally createrepo is run.

"""

import pwd
import os
import sys
import xmlrpclib
import lxml.etree as ET
import logging
import urllib2
from optparse import OptionParser

import turbogears.config
from turbogears.database import session

from bkr.common.helpers import atomically_replaced_file, unlink_ignore, siphon
from bkr.server.model import TaskLibrary, Task
from bkr.server.util import load_config

# We need kobo
try:
    import kobo.xmlrpc
    from kobo.client import HubProxy
except ImportError:
    print 'Please install kobo client library'
    sys.exit(1)

__description__ = 'Script to sync local task RPMs from a remote Beaker instance'
__version__ = '0.1'


# Helper function which doesn't need to be a class method
def find_task_version_url(task_xml):

    xml = ET.fromstring(task_xml)
    return xml.find('.').attrib['version'], \
        xml.find('./rpms/rpm').attrib['url']

class TaskLibrarySync:

    def __init__(self, remote=None):

        # setup, sanity checks
        self.task_dir = turbogears.config.get("basepath.rpms", "/var/www/beaker/rpms")
        self._setup_logging()

        # Initialize core attributes
        if remote:
            self.remote = remote.rstrip("/")
            remote_proxy = self._get_server_proxy(self.remote)
            self.proxy={'remote':remote_proxy,
                        }

        self.tasks_added = []
        self.t_downloaded = 0
        self.tasklib = TaskLibrary()
        # load configuration data
        load_config()

    def _setup_logging(self):
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        self.logger = logging.getLogger("")
        self.logger.addHandler(stdout_handler)

    def check_perms(self):
        # See if the euid is the same as that of self.task_dir
        task_dir_uid = os.stat(self.task_dir).st_uid

        if os.geteuid() != task_dir_uid:
            self.logger.critical('You should run this script as user: %s' % pwd.getpwuid(task_dir_uid).pw_name)
            sys.exit(-1)

    def _get_server_proxy(self, server):

        kobo_conf = {}
        kobo_conf['HUB_URL'] = server
        hub = HubProxy(kobo_conf)

        return hub

    def get_tasks(self, server):

        # if local, directly read the database
        if server == 'local':
            tasks = Task.query.filter(Task.valid == True).all()
            tasks = [task.to_dict() for task in tasks]
        else:
            tasks = self.proxy[server].tasks.filter({'valid':1})

        return [task['name'] for task in tasks]

    def _get_task_xml(self, server, task):

        # if local, directly read the database
        if server == 'local':
            try:
                self.logger.debug('Getting task XML for %s from local database' % task)
                return Task.by_name(task, True).to_xml(False)
            except Exception:
                self.logger.error('Could not get task XML for %s from local Beaker DB. Continuing.' % task)
                return None

        try:
            self.logger.debug('Getting task XML for %s from %s' % (task, getattr(self, server)))
            return self.proxy[server].tasks.to_xml(task, False)
        except (xmlrpclib.Fault, xmlrpclib.ProtocolError) as e:
            # If something goes wrong with this task, for example:
            # https://bugzilla.redhat.com/show_bug.cgi?id=915549
            # we do our best to continue anyway...
            self.logger.error('Could not get task XML for %s from %s. Continuing.' % (task, server))
            self.logger.error('Error message: %s' % e)
            return None

    def update_db(self):

        self.logger.info('Updating local Beaker database..')

        for task_rpm in self.tasks_added:

            self.logger.debug('Adding %s'% task_rpm)

            with open(os.path.join(self.task_dir,task_rpm)) as task_data:
                try:
                    def write_data(f):
                        siphon(task_data, f)
                    session.begin()
                    task = self.tasklib.update_task(task_rpm, write_data)
                    session.commit()
                except Exception, e:
                    session.rollback()
                    session.close()
                    self.logger.exception('Error adding task %s: %s' % (task_rpm, e))
                    unlink_ignore(os.path.join(self.task_dir, task_rpm))

                else:
                    session.close()
                    self.logger.debug('Successfully added %s' % task.rpm)

        # Update task repo
        self.logger.info('Creating repodata..')
        self.tasklib.update_repo()

        return

    def _download(self, task_url):

        task_rpm_name = os.path.split(task_url)[1]
        rpm_file = os.path.join(self.task_dir, task_rpm_name)

        if not os.path.exists(rpm_file):

            try:
                with atomically_replaced_file(rpm_file) as f:
                    siphon(urllib2.urlopen(task_url), f)
                    f.flush()

            except urllib2.HTTPError as err:
                self.logger.exception('Error downloading %s: %s' % (task_rpm_name, err))
                unlink_ignore(rpm_file)

            except Exception as err:
                self.logger.exception('Error downloading %s: %s' % (task_rpm_name, err))
                unlink_ignore(rpm_file)
            else:
                self.logger.debug('Downloaded %s' % task_rpm_name)
                self.tasks_added.append(task_rpm_name)
                self.t_downloaded = self.t_downloaded + 1

        else:
            self.logger.debug('Already downloaded %s' % task_rpm_name)
            self.tasks_added.append(task_rpm_name)
            self.t_downloaded = self.t_downloaded + 1

        return

    def tasks_add(self, new_tasks, old_tasks):

        self.logger.info('Downloading %s new tasks' % len(new_tasks))

        # Get the task XMLs
        task_xml = []
        for task in new_tasks:
            task_xml = self._get_task_xml('remote', task)
            if task_xml is not None:
                task_url = find_task_version_url(task_xml)[1]
                self._download(task_url)

        # common tasks
        self.logger.info('Downloading %s common tasks' % len(old_tasks))

        # tasks which exist in both remote and local
        # will be uploaded only if remote_version != local_version
        for task in old_tasks:
            remote_task_xml = self._get_task_xml('remote', task)
            local_task_xml = self._get_task_xml('local', task)

            if None not in [remote_task_xml, local_task_xml]:
                remote_task_version, remote_task_url = find_task_version_url(remote_task_xml)
                local_task_version = find_task_version_url(local_task_xml)[0]

                if remote_task_version != local_task_version:
                    self._download(remote_task_url)

        # Finished downloading tasks
        self.logger.info('Downloaded %d Tasks' % self.t_downloaded)

        # update Beaker's database
        self.update_db()

        return

    # Get list of tasks from remote and local
    # return the common tasks and the new tasks
    # not present locally
    def tasks(self):
        self.logger.info('Getting the list of tasks from remote and local Beaker..')
        remote_tasks = self.get_tasks('remote')
        local_tasks = self.get_tasks('local')
        # new_tasks -> Tasks which do not exist on the local
        # old_tasks-> Tasks which exist on remote and local
        new_tasks = list(set(remote_tasks).difference(local_tasks))
        old_tasks = list(set(remote_tasks).intersection(local_tasks))

        return old_tasks, new_tasks

def get_parser():

    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__, version=__version__)

    parser.add_option('--remote', dest='remote',
                      help='Remote Beaker Instance',
                     metavar='remote')

    parser.add_option('--force', action='store_true',dest='force',default=False,
                      help='Do not ask before overwriting task RPMs')

    parser.add_option('--debug', action='store_true',dest='debug',default=False,
                      help='Display all messages')

    return parser

def main():

    parser = get_parser()
    (options, args) = parser.parse_args()

    # Sanity check
    if options.remote is None:
        parser.print_help()
        sys.exit(1)

    task_sync = TaskLibrarySync(options.remote)
    task_sync.check_perms()

    if options.debug:
        task_sync.logger.setLevel(logging.DEBUG)
    else:
        task_sync.logger.setLevel(logging.INFO)

    old_tasks, new_tasks = task_sync.tasks()

    if not options.force:
        if len(old_tasks)>0:
            task_sync.logger.warning('Warning: %d tasks already present may be overwritten '
                            'with the version from %s if the two versions are different' % (len(old_tasks), task_sync.remote))

        proceed = raw_input('Proceed with task addition? (y/n) ')
        if proceed.lower() == 'y':
            proceed = True
        else:
            proceed = False
    else:
        proceed = True

    if proceed:
        task_sync.tasks_add(new_tasks, old_tasks)
    else:
        task_sync.logger.info('Task syncing aborted.')

    return

# Begin here
if __name__ == '__main__':
    main()
