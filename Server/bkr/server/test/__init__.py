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

from bkr.server.util import load_config
import turbogears as tg
import sqlalchemy as sqla
import unittest
import logging
import os
import time

log = logging.getLogger(__name__)

class BeakerTest(unittest.TestCase):

    CONFIG_FILE='test.cfg' #Fixme, get this from opts perhaps?    


class DataSetup(object):
 
    setup_success = False
    ran_setup = False

    @classmethod
    def _create_engine(cls):
        engine = sqla.create_engine("mysql://beaker:beaker@localhost")
        e = engine.connect().execute
        return e

    @classmethod
    def setup_model(cls,override=True):
        has_run_setup = cls.ran_setup
        if not has_run_setup or override:
            try:
                from bkr.server.tools.init import init_db
                db_name = str(tg.config.get('db_name'))
                e = cls._create_engine()
                if override:
                    e("DROP DATABASE IF EXISTS %s" % db_name)
                e("CREATE DATABASE %s" % db_name)
                init_db()
            except Exception, e:
                log.error('Setup failed: %s' % e)
                cls.ran_setup = True
                return False
            cls.setup_success = True
            return True
        else:
            if cls.setup_success:
                return True
            else:
                log.debug('Setup previously ran and failed')
                return False
    
    @classmethod
    def destroy_model(cls): 
        setup_success = cls.setup_success
        if not setup_success :
            log.debug('Cannot destroy model which has not been created')
            return False
        else:
            try:
                e = cls._create_engine()
                e("DROP DATABASE %s" % tg.config.get('db_name'))
                return True
            except Exception, e:
                log.error('Could not drop database: %s' % e)
                return False

def setup_package():
    log.info('Loading test configuration from %s', BeakerTest.CONFIG_FILE)
    load_config(BeakerTest.CONFIG_FILE)
    DataSetup.setup_model()
    from bkr.server.test.data_setup import create_labcontroller
    create_labcontroller() #always need a labcontroller

def teardown_package():
    pass

