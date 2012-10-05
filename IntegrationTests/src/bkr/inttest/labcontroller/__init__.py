import logging
import os
import signal
from urlparse import urlparse, urlunparse
from bkr.labcontroller.config import load_conf, get_conf
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest import Process
log = logging.getLogger(__name__)

# XXX this should be inside setup_package, but lots of code in
# bkr.labcontroller assumes it has been configured at import time
config_file = os.environ.get('BEAKER_LABCONTROLLER_CONFIG_FILE', 'labcontroller-test.cfg')
log.info('Loading LC test configuration from %s', config_file)
assert os.path.exists(config_file) , 'Config file %s must exist' % config_file
load_conf(config_file)

processes = []

def setup_package():
    conf = get_conf()
    if os.path.exists('../.git'):
        with session.begin():
            user = data_setup.create_user(user_name=conf.get('USERNAME').decode('utf8'), password=conf.get('PASSWORD'))
            lc = data_setup.create_labcontroller(fqdn='localhost', user=user)

def start_proxy():

    if 'LAB_CONTROLLER_BASE_URL' not in os.environ:
        # Let's start the proxy server if we don't
        # have a real one
        p = Process('beaker-proxy',
                    args=['python', '../LabController/src/bkr/labcontroller/main.py',
                          '-c', config_file, '-f'],
                    listen_port=8000,
                    stop_signal=signal.SIGTERM)
        processes.append(p)
        try:
            p.start()
        except:
            p.stop()
            raise
        return 'http://localhost:8000/server'
    else:
        # We have been passed a space seperated list of LCs
        lab_controllers = os.environ.get('LAB_CONTROLLER_BASE_URL')
        lab_controllers_list = lab_controllers.split()
        # Just get the last one, it shouldn't matter to us
        lab_controller = lab_controllers_list.pop()
        parsed_url = urlparse(lab_controller)
        parsed_url.port = 8000
        parsed_url.path = '/server'
        return urlunparse(parsed_url)

def teardown_package():
    for process in processes:
        process.stop()
