
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import with_statement
from alembic import context
from turbogears.database import get_engine
from bkr.server.util import load_config_or_exit
from turbogears import config

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from bkr.server.model import base

target_metadata = base.DeclarativeMappedObject.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    load_config_or_exit()
    url = config.get("sqlalchemy.dburi")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    load_config_or_exit()
    engine = get_engine()

    # In case you are trying to perform column change (size for example)
    # alembic will not handle this automatically.
    # Additional parameter has to be passed into context.configure(compare_type=True)
    # Be aware that output of this can be error-pone. Especially for dialect.
    # We want to keep dialect tight with SQLAlchemy all the time.
    # So in case migration contains import to MySQL dialect (MySQL is used as main backend)
    # then this migration has to written manually - But migration content can still help you
    # how to perform this migration
    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
