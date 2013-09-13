
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
from turbogears.database import session
import cherrypy
import cherrypy._cpwsgi
from cherrypy.filters.basefilter import BaseFilter
from flask import Flask
from bkr.server import identity

log = logging.getLogger(__name__)

# Load config.
from bkr.log import log_to_stream
from bkr.server.util import load_config
load_config()
log_to_stream(sys.stderr, level=logging.DEBUG)

# This is NOT the right way to do this, we should just use SCRIPT_NAME properly instead.
# But this is needed to line up with TurboGears server.webpath way of doing things.
class PrefixedFlask(Flask):
    def add_url_rule(self, rule, *args, **kwargs):
        prefixed_rule = config.get('server.webpath', '').rstrip('/') + rule
        return super(PrefixedFlask, self).add_url_rule(prefixed_rule, *args, **kwargs)

app = application = PrefixedFlask('bkr.server', static_folder='../../assets')

# Register all routes.
import bkr.server.controllers

@app.before_first_request
def init():
    # Make TG's run_with_transaction a no-op, we manage the transaction here 
    # through Flask instead.
    import turbogears.database
    def run_with_transaction_noop(func, *args, **kwargs):
        return func(*args, **kwargs)
    turbogears.database.run_with_transaction = run_with_transaction_noop
    class EndTransactionsFilterNoop(BaseFilter): pass
    turbogears.database.EndTransactionsFilter = EndTransactionsFilterNoop
    turbogears.startup.EndTransactionsFilter = EndTransactionsFilterNoop

    # Make TG's restart_transaction not call session.close(). We are 
    # responsible for calling session.close() here at the very end of the 
    # Flask request, and if TG does it during its validation error handling, it 
    # will break identity.
    def restart_transaction_patched(args):
        session.rollback()
        session.begin()
    turbogears.database.restart_transaction = restart_transaction_patched

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

# NOTE: order of before_request/after_request functions is important!
# Flask runs them in the reverse of the order in which they were added.

@app.before_request
def begin_session():
    session.begin()

@app.after_request
def commit_or_rollback_session(response):
    # Matches behaviour of TG's sa_rwt: commit on success or redirect, 
    # roll back on error.
    if session.is_active:
        if response.status_code >= 200 and response.status_code < 400:
            session.commit()
        else:
            log.debug('Rolling back for %s response', response.status_code)
            session.rollback()
    return response

@app.teardown_appcontext
def close_session(exception=None):
    try:
        if session.is_active:
            log.warn('Session active when tearing down app context, rolling back')
            session.rollback()
        session.close()
    except Exception, e:
        # log and suppress
        log.exception('Error closing session when tearing down app context')

app.before_request(identity.check_authentication)
app.after_request(identity.update_response)

@app.after_request
def fall_back_to_cherrypy(response):
    # If Flask returns a 404, fall back to the old CherryPy stuff.
    if response.status_code == 404:
        # XXX is it safe to discard the old response without consuming it?
        return app.make_response(cherrypy._cpwsgi.wsgiApp)
    return response
