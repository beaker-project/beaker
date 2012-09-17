import sys
sys.stdout = sys.stderr
import __main__
__main__.__requires__ = ['TurboGears']
import pkg_resources
import resource

import os
os.environ['PYTHON_EGG_CACHE'] = '/var/www/.python-eggs'

import atexit
import cherrypy
import cherrypy._cpwsgi
import turbogears

from bkr.server.util import load_config
from turbogears import config
load_config()

# If rlimit_as is defined in the config file then set the limit here.
if config.get('rlimit_as'):
    resource.setrlimit(resource.RLIMIT_AS, (config.get('rlimit_as'),
                                            config.get('rlimit_as')))

turbogears.config.update({'global': {'server.environment': 'production'}})
turbogears.config.update({'global': {'autoreload.on': False}})
turbogears.config.update({'global': {'server.log_to_screen': False}})

import bkr.server.controllers
cherrypy.root = bkr.server.controllers.Root()

if cherrypy.server.state == 0:
    atexit.register(cherrypy.server.stop)
    cherrypy.server.start(init_only=True, server_class=None)

# workaround for TGMochiKit initialisation
# https://sourceforge.net/p/turbogears1/tickets/34/
import tgmochikit
from turbogears.widgets.base import register_static_directory
tgmochikit.init(register_static_directory, config)

application = cherrypy._cpwsgi.wsgiApp
