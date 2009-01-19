import sys
sys.stdout = sys.stderr
import pkg_resources
pkg_resources.require("CherryPy<3.0")

import os
os.environ['PYTHON_EGG_CACHE'] = '/var/www/.python-eggs'

import atexit
import cherrypy
import cherrypy._cpwsgi
import turbogears
from sqlalchemy.exceptions import InvalidRequestError


from medusa.util import load_config
load_config()

turbogears.config.update({'global': {'server.environment': 'production'}})
turbogears.config.update({'global': {'autoreload.on': False}})
turbogears.config.update({'global': {'server.log_to_screen': False}})

from medusa.model import UserSystem

def check_password(environ, user, password):
    try:
        machineuser = UserSystem.query().filter_by(system_name=user).one()
    except InvalidRequestError:
        return None
    if machineuser.password == password:
        return True
    return False
