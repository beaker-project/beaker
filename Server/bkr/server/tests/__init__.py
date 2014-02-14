import os
import sys
import logging
from bkr.server.util import load_config
from bkr.log import log_to_stream
from turbogears.database import metadata, get_engine

_config_file = os.environ.get('BEAKER_CONFIG_FILE')
def setup_package():
    assert os.path.exists(_config_file), 'Config file %s must exist' % _config_file
    load_config(configfile=_config_file)
    log_to_stream(sys.stdout, level=logging.DEBUG)
    get_engine()
    metadata.create_all()
