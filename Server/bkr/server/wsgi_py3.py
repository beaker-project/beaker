
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
WSGI entry point for the Flask application on Python 3.

Boots only the migrated Flask endpoints, without the legacy
CherryPy/TurboGears stack. Endpoint modules are registered here as they
become importable on Python 3.
"""

import sys
import logging

from bkr.log import log_to_stream
from bkr.server.util import load_config
from bkr.server.database import session
from bkr.common import __version__
from bkr.server import identity
from bkr.server.app import app

load_config()
log_to_stream(sys.stderr, level=logging.DEBUG)

log = logging.getLogger(__name__)

application = app

import bkr.server.authentication
import bkr.server.activity
import bkr.server.power
import bkr.server.user
import bkr.server.labcontroller
import bkr.server.systems
import bkr.server.group
import bkr.server.pools
import bkr.server.tasks
import bkr.server.jobs
import bkr.server.recipes
import bkr.server.recipesets
import bkr.server.recipetasks
import bkr.server.reserve_workflow
import bkr.server.kickstart

import bkr.server.rpc.root
import bkr.server.rpc.authentication
import bkr.server.rpc.distrotrees
import bkr.server.rpc.distros
import bkr.server.rpc.group
import bkr.server.rpc.labcontroller
import bkr.server.rpc.prefs
import bkr.server.rpc.taskactions
import bkr.server.rpc.tasks
import bkr.server.rpc.user
import bkr.server.rpc.systems
import bkr.server.rpc.jobs
import bkr.server.rpc.recipes
import bkr.server.rpc.recipesets
import bkr.server.rpc.watchdogs
import bkr.server.rpc.dispatch


@app.before_request
def begin_session():
    session.begin()


@app.after_request
def commit_or_rollback_session(response):
    if session.is_active:
        if 200 <= response.status_code < 400:
            session.commit()
        else:
            session.rollback()
    return response


@app.after_request
def set_extra_headers(response):
    response.headers.add('X-Beaker-Version', __version__)
    response.headers.add('Vary', 'Accept')
    return response


@app.teardown_appcontext
def close_session(exception=None):
    session.close()


app.before_request(identity.check_authentication)
app.after_request(identity.update_response)
