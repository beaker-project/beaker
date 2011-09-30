import logging
import os
from kobo.conf import PyConfigParser
from turbogears.database import session
from bkr.inttest import data_setup
log = logging.getLogger(__name__)

def setup_package():
    global conf, lc
    config_file = os.environ.get('BEAKER_LABCONTROLLER_CONFIG_FILE', 'labcontroller-test.cfg')
    log.info('Loading LC test configuration from %s', config_file)

    assert os.path.exists(config_file) , 'Config file %s must exist' % config_file
    # Make sure you don't have a system wide config in place...
    conf = PyConfigParser()
    conf.load_from_file(config_file)

    user = data_setup.create_user(user_name=conf.get('USERNAME').decode('utf8'), password=conf.get('PASSWORD'))
    session.flush()
    lc = data_setup.create_labcontroller(user=user)
