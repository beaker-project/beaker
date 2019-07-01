
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
WSGI application entry point.

Normal Beaker code should not import this module, since it has side effects
(such as loading configuration). It should only be imported by the WSGI
application container.
"""

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

import os
import sys
import logging
from turbogears import config
from turbogears.database import session
import cherrypy
import cherrypy._cpwsgi
from cherrypy.filters.basefilter import BaseFilter
from flask import Flask
from bkr.common import __version__
from bkr.server import identity, assets
from bkr.server.app import app

log = logging.getLogger(__name__)

# Load config.
from bkr.log import log_to_stream
from bkr.server.util import load_config
load_config()
log_to_stream(sys.stderr, level=logging.DEBUG)

# Keep the code before the imports, otherwise we'll end up with function names
# not marked as executed (see: Coverage.py FAQ)
if config.get('coverage', False):
    import coverage
    import atexit

    log.debug('Starting coverage analysis')
    cov = coverage.coverage(data_suffix=True, cover_pylib=False, timid=True, omit=['*.kid'])
    cov.start()

    def save_coverage():
        log.debug('Saving coverage')
        cov.stop()
        cov.save()

    atexit.register(save_coverage)


application = app

# Register all routes.
import bkr.server.authentication
import bkr.server.activity
import bkr.server.user
import bkr.server.group
import bkr.server.systems
import bkr.server.reserve_workflow
import bkr.server.pools
import bkr.server.jobs
import bkr.server.recipesets
import bkr.server.recipes
import bkr.server.recipetasks
import bkr.server.power
import bkr.server.labcontroller
import bkr.server.tasks
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
    import bkr.server.controllers
    cherrypy.root = bkr.server.controllers.Root()
    cherrypy.server.start(init_only=True, server_class=None)

    # If rlimit_as is defined in the config file then set the limit here.
    if config.get('rlimit_as'):
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (config.get('rlimit_as'),
                                                config.get('rlimit_as')))

    # Build assets. If assets.auto_build is True in the config, this will also
    # happen on page request. Otherwise, it only happens once at startup here.
    assets.build_assets()

    # workaround for TGMochiKit initialisation
    # https://sourceforge.net/p/turbogears1/tickets/34/
    import tgmochikit
    from turbogears.widgets.base import register_static_directory
    tgmochikit.init(register_static_directory, config)

    # Global device class list... a terrible hack, desperately needs deleting
    from bkr.server import model
    with session.begin():
        model.device_classes = [c.device_class for c in model.DeviceClass.query]

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

@app.after_request
def set_extra_headers(response):
    response.headers.add('X-Beaker-Version', __version__)
    # Most of our request handlers are doing content negotation, so we need to specify
    # "Vary: Accept" header unconditionally.
    response.headers.add('Vary', 'Accept')
    return response

@app.teardown_appcontext
def close_session(exception=None):
    try:
        session.close()
    except Exception:
        # If session.close() fails the application is now totally useless:
        # the next request will fail to start a new transaction because we have
        # not closed the old one here. So we kill the entire process with
        # SIGABRT. The application container should spawn a fresh worker to
        # replace this one.
        # Note that the most likely failure here is MemoryError, so we must not
        # do any other work before we abort (not even logging a message)
        # because that could try to allocate, which will just fail again with
        # MemoryError.
        os.abort()

app.before_request(identity.check_authentication)
app.after_request(identity.update_response)

@app.after_request
def fall_back_to_cherrypy(flask_response):
    # If Flask returns a 404, fall back to the old CherryPy stuff.
    if flask_response.status_code == 404:
        cherrypy_response = app.make_response(cherrypy._cpwsgi.wsgiApp)
        # If we get a 404 from cherrypy as well, it means that the
        # resource doesn't exist, so we return the original response
        if cherrypy_response.status_code == 404:
            cherrypy_response.close()
            return flask_response
        else:
            flask_response.close()
            return cherrypy_response

    return flask_response
