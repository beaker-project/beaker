
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import logging
from bkr.server.util import load_config
from bkr.log import log_to_stream
from bkr.server.tests import data_setup

_config_file = os.environ.get('BEAKER_CONFIG_FILE')
def setup_package():
    assert os.path.exists(_config_file), 'Config file %s must exist' % _config_file
    load_config(configfile=_config_file)
    log_to_stream(sys.stdout, level=logging.DEBUG)
    data_setup.setup_model()
