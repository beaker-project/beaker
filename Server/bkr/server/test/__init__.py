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

import os
import logging
from turbogears import update_config
from turbogears.database import session
import turbomail.adapters.tg1
from bkr.server.test import data_setup

log = logging.getLogger(__name__)

CONFIG_FILE='test.cfg' #Fixme, get this from opts perhaps?    

def setup_package():
    log.info('Loading test configuration from %s', CONFIG_FILE)
    assert os.path.exists(CONFIG_FILE), 'Config file %s must exist' % CONFIG_FILE
    update_config(configfile=CONFIG_FILE, modulename='bkr.server.config')
    data_setup.setup_model()
    data_setup.create_distro()
    data_setup.create_labcontroller() #always need a labcontroller
    session.flush()
    turbomail.adapters.tg1.start_extension()

def teardown_package():
    turbomail.adapters.tg1.shutdown_extension()

