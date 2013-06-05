import logging
import os
import shutil
import signal
import unittest
from socket import gethostname
from urlparse import urlparse, urlunparse
from bkr.labcontroller.config import load_conf, get_conf
from turbogears.database import session
from bkr.server.model import LabController
from bkr.inttest import data_setup
from bkr.inttest import Process
log = logging.getLogger(__name__)

# XXX this should be inside setup_package, but lots of code in
# bkr.labcontroller assumes it has been configured at import time
config_file = os.environ.get('BEAKER_LABCONTROLLER_CONFIG_FILE', 'labcontroller-test.cfg')
log.info('Loading LC test configuration from %s', config_file)
assert os.path.exists(config_file) , 'Config file %s must exist' % config_file
load_conf(config_file)

if 'BEAKER_LABCONTROLLER_HOSTNAME' in os.environ:
    running_dogfood_task = True
else:
    running_dogfood_task = False

processes = []
lc_fqdn = None

class LabControllerTestCase(unittest.TestCase):

    def get_lc_fqdn(self):
        return lc_fqdn

    def get_lc(self):
        return LabController.by_name(self.get_lc_fqdn())

    def get_proxy_url(self):
        return 'http://%s:8000/' % lc_fqdn

    def get_log_base_url(self):
        protocol = get_conf().get('URL_SCHEME', 'http')
        server_name = get_conf().get_url_domain()
        return '%s://%s' % (protocol, server_name)

def setup_package():
    global lc_fqdn
    conf = get_conf()

    if not running_dogfood_task:
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
