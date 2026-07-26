import os
import pathlib

import sqlalchemy
import connexion
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


basedir = pathlib.Path(__file__).parent.resolve()
connex_app = connexion.App(__name__, specification_dir=basedir)

app = connex_app.app
app.config.from_object("bkr.settings")
app.config.from_object(os.environ.get("BKR_SETTINGS_MODULE"))

config = app.config
db = SQLAlchemy(app)
ma = Marshmallow(app)


def get_engine(db_uri):
    return sqlalchemy.create_engine(
        db_uri,
        pool_size=app.config["SQLALCHEMY_POOL_SIZE"],
        max_overflow=app.config["SQLALCHEMY_MAX_OVERFLOW"],
        encoding="utf8",
    )

