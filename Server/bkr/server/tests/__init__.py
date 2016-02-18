
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import logging
from turbogears.database import get_engine
from sqlalchemy import event
from bkr.server.util import load_config
from bkr.log import log_to_stream
from bkr.server.tests import data_setup

# Workarounds for Python sqlite busted behaviour
# http://docs.sqlalchemy.org/en/rel_1_0/dialects/sqlite.html#pysqlite-serializable
def workaround_sqlite_begin():
    engine = get_engine()
    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None
    @event.listens_for(engine, "begin")
    def do_begin(conn):
        # emit our own BEGIN
        conn.execute("BEGIN")

_config_file = os.environ.get('BEAKER_CONFIG_FILE')
def setup_package():
    assert os.path.exists(_config_file), 'Config file %s must exist' % _config_file
    load_config(configfile=_config_file)
    log_to_stream(sys.stdout, level=logging.DEBUG)
    workaround_sqlite_begin()
    data_setup.setup_model()
