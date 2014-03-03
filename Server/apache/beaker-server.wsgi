import sys
sys.stdout = sys.stderr
import __main__
__main__.__requires__ = ['TurboGears', 'Flask']
import pkg_resources

import os
os.environ['PYTHON_EGG_CACHE'] = '/var/www/.python-eggs'

from bkr.server.wsgi import application

import turbogears
turbogears.config.update({'global': {'server.environment': 'production'}})

from bkr.log import log_to_syslog
log_to_syslog('beaker-server')
