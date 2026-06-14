
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy import MetaData, create_engine
from sqlalchemy import __version__ as _sqlalchemy_version
from sqlalchemy.orm import scoped_session, create_session

metadata = MetaData()

_SQLALCHEMY_GE_14 = tuple(
    int(part) for part in _sqlalchemy_version.split('.')[:2]) >= (1, 4)


def bind_metadata():
    if metadata.bind is not None:
        return
    from bkr.server.app import app
    engine_args = {}
    for key, value in app.config.items():
        if 'sqlalchemy' in key:
            engine_args[key.rsplit('.', 1)[-1]] = value
    dburi = engine_args.pop('dburi')
    metadata.bind = create_engine(dburi, **engine_args)


def get_engine():
    bind_metadata()
    return metadata.bind


def _make_session():
    bind_metadata()
    return create_session()


session = scoped_session(_make_session)


def session_connection(mapper):
    # SQLAlchemy 1.4 dropped the positional mapper argument to
    # Session.connection() in favor of bind_arguments.
    if _SQLALCHEMY_GE_14:
        return session.connection(bind_arguments={'mapper': mapper})
    return session.connection(mapper)
