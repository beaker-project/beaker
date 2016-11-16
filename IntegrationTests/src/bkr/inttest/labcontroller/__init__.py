
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import os
import shutil
import signal
from socket import gethostname
from urlparse import urlparse, urlunparse
from bkr.labcontroller.config import load_conf, get_conf
from turbogears.database import session
from bkr.server.model import LabController, Watchdog, Recipe, RecipeSet, \
        System, SystemStatus
from bkr.inttest import data_setup, Process, DatabaseTestCase
log = logging.getLogger(__name__)

# XXX this should be inside setup_package, but lots of code in
# bkr.labcontroller assumes it has been configured at import time
config_file = os.environ.get('BEAKER_LABCONTROLLER_CONFIG_FILE', 'labcontroller-test.cfg')
log.info('Loading LC test configuration from %s', config_file)
assert os.path.exists(config_file) , 'Config file %s must exist' % config_file
load_conf(config_file)

processes = []
lc_fqdn = None
_daemons_running_externally = False

def daemons_running_externally():
    return _daemons_running_externally

class LabControllerTestCase(DatabaseTestCase):

    def __init__(self, *args, **kwargs):
        super(LabControllerTestCase, self).__init__(*args, **kwargs)
        self.addCleanup(self._check_lc_leaks)

    @staticmethod
    def get_lc():
        return LabController.by_name(lc_fqdn)

    @staticmethod
    def get_proxy_url():
        return 'http://%s:8000/' % lc_fqdn

    @staticmethod
    def get_log_base_url():
        protocol = get_conf().get('URL_SCHEME', 'http')
        server_name = get_conf().get_url_domain()
        return '%s://%s' % (protocol, server_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1336272
    def _check_lc_leaks(self):
        with session.begin():
            lc = LabController.by_name(lc_fqdn)
            # check for outstanding watchdogs
            watchdogs = Watchdog.query\
                .join(Watchdog.recipe).join(Recipe.recipeset)\
                .filter(RecipeSet.lab_controller == lc)
            if watchdogs.count():
                # If your test case hits this error, you need to fix it so that 
                # any running recipes are cancelled otherwise beaker-watchdog 
                # will eventually pick them up and abort them, interfering with 
                # some later test.
                raise AssertionError('Leaked watchdogs for %s: %s'
                        % (lc_fqdn, watchdogs.all()))
            # check for systems left associated to the LC
            systems = System.query.filter(System.lab_controller == lc)
            if systems.count():
                # If your test case hits this error, you need to fix it so that 
                # any systems which were associated to the LC are 
                # de-associated, otherwise subsequent tests which invoke the 
                # scheduler will try to schedule recipes onto the system and 
                # then beaker-provision will start trying to run the 
                # provisioning commands.
                raise AssertionError('Leaked systems for %s: %s'
                        % (lc_fqdn, systems.all()))

    # Helper methods for ensuring the above conditions are met:

    def cleanup_system(self, system):
        with session.begin():
            session.expire(system)
            system.status = SystemStatus.removed
            system.lab_controller = None

    def cleanup_job(self, job):
        with session.begin():
            job.cancel(msg=u'Cancelled by cleanup_job in tests')
            job.update_status()
            session.flush()
            for recipe in job.all_recipes:
                if hasattr(recipe.resource, 'system'):
                    recipe.resource.system.status = SystemStatus.removed
                    recipe.resource.system.lab_controller = None

def setup_package():
    global lc_fqdn, _daemons_running_externally
    conf = get_conf()

    if not 'BEAKER_LABCONTROLLER_HOSTNAME' in os.environ:
        # Need to start the lab controller daemons ourselves
        with session.begin():
            user = data_setup.create_user(user_name=conf.get('USERNAME').decode('utf8'), password=conf.get('PASSWORD'))
            lc = data_setup.create_labcontroller(fqdn=u'localhost', user=user)
        processes.extend([
            Process('beaker-proxy',
                    args=['python', '../LabController/src/bkr/labcontroller/main.py',
                          '-c', config_file, '-f'],
                    listen_port=8000,
                    stop_signal=signal.SIGTERM),
            Process('beaker-provision',
                    args=['python', '../LabController/src/bkr/labcontroller/provision.py',
                          '-c', config_file, '-f'],
                    stop_signal=signal.SIGTERM),
            Process('beaker-watchdog',
                    args=['python', '../LabController/src/bkr/labcontroller/watchdog.py',
                          '-c', config_file, '-f'],
                    stop_signal=signal.SIGTERM),
        ])
        lc_fqdn = u'localhost'
    else:
        _daemons_running_externally = True
        # We have been passed a space seperated list of LCs
        lab_controllers = os.environ.get('BEAKER_LABCONTROLLER_HOSTNAME').decode('utf8')
        lab_controllers_list = lab_controllers.split()
        # Just get the last one, it shouldn't matter to us
        lab_controller = lab_controllers_list.pop()
        # Make sure that the LC is in the DB
        data_setup.create_labcontroller(fqdn=lab_controller)
        lc_fqdn = lab_controller

    # Clear out any existing job logs, so that they are registered correctly 
    # when first created.
    # If we've been passed a remote hostname for the LC, we assume it's been 
    # freshly provisioned and the dir will already be empty.
    shutil.rmtree(conf.get('CACHEPATH'), ignore_errors=True)

    try:
        for process in processes:
            process.start()
    except:
        for process in processes:
            process.stop()
        raise

def teardown_package():
    for process in processes:
        process.stop()
