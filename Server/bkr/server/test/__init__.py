# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
from StringIO import StringIO
import logging, logging.config
import cherrypy
import turbogears
from turbogears import update_config
from turbogears.database import session
from bkr.server.controllers import Root
from bkr.server.util import log_to_stream
from bkr.server.test import data_setup

# hack to make turbogears.testutil not do dumb stuff at import time
orig_cwd = os.getcwd()
os.chdir('/tmp')
import turbogears.testutil
os.chdir(orig_cwd)

# workaround for weird sqlalchemy-0.4 bug :-S
# http://markmail.org/message/rnnzdebfzrjt3kmi
from sqlalchemy.orm.dynamic import DynamicAttributeImpl
DynamicAttributeImpl.accepts_scalar_loader = False

log = logging.getLogger(__name__)

CONFIG_FILE = os.environ.get('BEAKER_CONFIG_FILE', 'test.cfg')

def get_server_base():
    return os.environ.get('BEAKER_SERVER_BASE_URL',
        'http://localhost:%s/' % turbogears.config.get('server.socket_port'))

def setup_package():
    log.info('Loading test configuration from %s', CONFIG_FILE)
    assert os.path.exists(CONFIG_FILE), 'Config file %s must exist' % CONFIG_FILE
    update_config(configfile=CONFIG_FILE, modulename='bkr.server.config')

    # Override loaded logging config, in case we are using the server's config file
    # (we really always want our tests' logs to go to stdout, not /var/log/beaker/)
    log_to_stream(sys.stdout, level=logging.NOTSET)

    if not 'BEAKER_SKIP_INIT_DB' in os.environ:
        data_setup.setup_model()
        data_setup.create_distro()
        data_setup.create_labcontroller() #always need a labcontroller
        session.flush()

    if not os.path.exists(turbogears.config.get('basepath.rpms')):
        os.mkdir(turbogears.config.get('basepath.rpms'))

    cherrypy.root = Root()
    turbogears.testutil.start_cp()

def teardown_package():
    cherrypy.server.stop()
