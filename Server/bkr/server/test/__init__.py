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
from bkr.server.util import load_config
from bkr.server.tools.init import main as beaker_init
from bkr.server.model import System, User, Distro, LabController
from bkr.server.bexceptions import *
from bkr.server.tools import init
import turbogears as tg
import sqlalchemy as sqla
import unittest
import logging
import os
import time

log = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)


class BeakerTest(unittest.TestCase):

    CONFIG_FILE='test.cfg' #Fixme, get this from opts perhaps?    
    BEAKER_LOGIN_USER = 'admin'
    BEAKER_LOGIN_PASSWORD = 'testing'
    SERVER = '%s:%s' % (os.environ.get('SERVER','localhost'), tg.config.get('server.socket_port'))


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
                try:
                    tg.update_config(configfile=BeakerTest.CONFIG_FILE, modulename="bkr.server.config")
                except Exception, e:
                    raise Exception('Could not update config %s' % e)   
                db_name = str(tg.config.get('db_name'))
                e = cls._create_engine()
                if override:
                    e("DROP DATABASE IF EXISTS %s" % db_name)
                e("CREATE DATABASE %s" % db_name)
                beaker_init(configfile=BeakerTest.CONFIG_FILE)#FIXME, add switch so we can run from beaker-init script if we can
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

    @classmethod
    def create_labcontroller(cls,**kw):
        if kw.get('fqdn'):
            lc_fqdn = kw['fqdn']
        else:
            lc_fqdn = tg.config.get('lc_fqdn')

        try:
            lc = LabController.by_name(lc_fqdn)  
        except Exception, e: #Doesn't exist ?
            if  '%s' % e == 'No rows returned for one()':
                lc = LabController(fqdn=lc_fqdn)
                return True
            else:
                raise

        log.debug('labcontroller %s already exists' % lc_fqdn)
        return True

def setup_package():
    load_config(BeakerTest.CONFIG_FILE)
    DataSetup.setup_model()
    DataSetup.create_labcontroller() #always need a labcontroller

def teardown_package():
    pass

