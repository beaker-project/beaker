
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

__requires__=['TurboGears']

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

from bkr.common.helpers import siphon
from bkr.server.model import TaskLibrary, Task
from bkr.server.util import load_config

from bkr.common import __version__
__description__ = 'Script to sync local task RPMs from a remote Beaker instance'

# Helper function which doesn't need to be a class method
def find_task_version_url(task_xml):

    xml = ET.fromstring(task_xml)
    return xml.find('.').attrib['version'], \
        xml.find('./rpms/rpm').attrib['url']

class TaskLibrarySync:


    batch_size = 100

    def __init__(self, remote=None):

        # load configuration data
        load_config()

        # setup, sanity checks
        self.task_dir = turbogears.config.get("basepath.rpms")

        self._setup_logging()

        # Initialize core attributes
        if remote:
            self.remote = remote.rstrip("/")
            self.proxy = xmlrpclib.ServerProxy(self.remote + '/RPC2')

        self.tasks_added = []
        self.t_downloaded = 0
        self.tasklib = TaskLibrary()

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

    def get_tasks(self, server):

        # if local, directly read the database
        if server == 'local':
            tasks = Task.query.filter(Task.valid == True).all()
            tasks = [task.to_dict() for task in tasks]
        else:
            tasks = self.proxy.tasks.filter({'valid':1})

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
            return self.proxy.tasks.to_xml(task, False)
        except (xmlrpclib.Fault, xmlrpclib.ProtocolError) as e:
            # If something goes wrong with this task, for example:
            # https://bugzilla.redhat.com/show_bug.cgi?id=915549
            # we do our best to continue anyway...
            self.logger.error('Could not get task XML for %s from %s. Continuing.' % (task, server))
            self.logger.error('Error message: %s' % e)
            return None

    def sync_tasks(self, urls_to_sync):
        """Syncs remote tasks to the local task library.

        sync_local_tasks() downloads tasks in batches and syncs
        them to the local task library. If the operation fails at some point
        any batches that have already been processed will be preserved.
        """
        def write_data_from_url(task_url):

            def _write_data_from_url(f):
                siphon(urllib2.urlopen(task_url), f)
                f.flush()

            return _write_data_from_url
        urls_to_sync.sort()
        tasks_and_writes = []
        for task_url in urls_to_sync:
            task_rpm_name = os.path.split(task_url)[1]
            tasks_and_writes.append((task_rpm_name, write_data_from_url(task_url),))
        # We section the batch processing up to allow other processes
        # that may be queueing for the flock to have access, and to limit
        # wastage of time if an error occurs
        total_number_of_rpms = len(tasks_and_writes)
        rpms_synced = 0
        while rpms_synced < total_number_of_rpms:
            session.begin()
            try:
                tasks_and_writes_current_batch = \
                    tasks_and_writes[rpms_synced:rpms_synced+self.batch_size]
                self.tasklib.update_tasks(tasks_and_writes_current_batch)
            except Exception, e:
                session.rollback()
                session.close()
                self.logger.exception('Error syncing tasks. Got error %s' % (unicode(e)))
                break
            session.commit()
            self.logger.debug('Synced %s tasks' % len(tasks_and_writes_current_batch))
            rpms_synced += self.batch_size
        session.close()

    def tasks_add(self, new_tasks, old_tasks):

        tasks_to_sync = []
        # Get the task XMLs
        task_xml = []
        for task in new_tasks:
            task_xml = self._get_task_xml('remote', task)
            if task_xml is not None:
                task_url = find_task_version_url(task_xml)[1]
                tasks_to_sync.append(task_url)

        # tasks which exist in both remote and local
        # will be uploaded only if remote_version != local_version
        for task in old_tasks:
            remote_task_xml = self._get_task_xml('remote', task)
            local_task_xml = self._get_task_xml('local', task)

            if None not in [remote_task_xml, local_task_xml]:
                remote_task_version, remote_task_url = find_task_version_url(remote_task_xml)
                local_task_version = find_task_version_url(local_task_xml)[0]

            if remote_task_version != local_task_version:
                tasks_to_sync.append(remote_task_url)

        number_of_tasks_to_sync = len(tasks_to_sync)
        rpms_synced = 0
        self.logger.info('Syncing %s tasks in total' % number_of_tasks_to_sync)
        try:
            self.sync_tasks(tasks_to_sync)
        except Exception, e:
            self.logger.exception(unicode(e))
            self.logger.info('Failed to sync all tasks')
        else:
            self.logger.info('Synced all tasks')

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
                                     'with the version from %s if the two versions are different' %
                                     (len(old_tasks), task_sync.remote))

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
