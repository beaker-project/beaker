
import __main__
__main__.__requires__ = ['CherryPy < 3.0']
import pkg_resources

# Terrible hack to prevent CherryPy from futzing with signal handlers on import
import signal
orig_signal_signal = signal.signal
signal.signal = lambda signum, handler: None
import cherrypy._cpengine
signal.signal = orig_signal_signal
del orig_signal_signal

import sys
import logging
from turbogears import config
import cherrypy
import cherrypy._cpwsgi
from flask import Flask

log = logging.getLogger(__name__)

app = Flask('bkr.server')
application = app

# Load config.
from bkr.log import log_to_stream
from bkr.server.util import load_config
load_config()
log_to_stream(sys.stderr, level=logging.DEBUG)

# Register all routes.
import bkr.server.controllers

@app.before_first_request
def init():
    # Set up old CherryPy stuff.
    cherrypy.root = bkr.server.controllers.Root()
    cherrypy.server.start(init_only=True, server_class=None)

    # If rlimit_as is defined in the config file then set the limit here.
    if config.get('rlimit_as'):
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (config.get('rlimit_as'),
                                                config.get('rlimit_as')))

    # workaround for TGMochiKit initialisation
    # https://sourceforge.net/p/turbogears1/tickets/34/
    import tgmochikit
    from turbogears.widgets.base import register_static_directory
    tgmochikit.init(register_static_directory, config)

    log.debug('Application initialised')

@app.after_request
def fall_back_to_cherrypy(response):
    # If Flask returns a 404, fall back to the old CherryPy stuff.
    if response.status_code == 404:
        # XXX is it safe to discard the old response without consuming it?
        return app.make_response(cherrypy._cpwsgi.wsgiApp)
    return response
