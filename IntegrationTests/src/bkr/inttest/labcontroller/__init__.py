import logging
import os
from bkr.labcontroller.config import load_conf, get_conf
from turbogears.database import session
from bkr.inttest import data_setup
log = logging.getLogger(__name__)

# XXX this should be inside setup_package, but lots of code in
# bkr.labcontroller assumes it has been configured at import time
config_file = os.environ.get('BEAKER_LABCONTROLLER_CONFIG_FILE', 'labcontroller-test.cfg')
log.info('Loading LC test configuration from %s', config_file)
assert os.path.exists(config_file) , 'Config file %s must exist' % config_file
load_conf(config_file)

def setup_package():
    conf = get_conf()
    with session.begin():
        user = data_setup.create_user(user_name=conf.get('USERNAME').decode('utf8'), password=conf.get('PASSWORD'))
        lc = data_setup.create_labcontroller(user=user)
