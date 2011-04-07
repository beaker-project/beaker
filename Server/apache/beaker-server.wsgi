import sys
sys.stdout = sys.stderr
import pkg_resources
pkg_resources.require("CherryPy<3.0")
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

application = cherrypy._cpwsgi.wsgiApp
