# Global parameters about the API itself
#
import os

HOST = os.getenv("API_HOST", "127.0.0.1")
PORT = int(os.getenv("API_PORT", "5000"))
DEBUG = True
JSONIFY_PRETTYPRINT_REGULAR = False

# Database (SQLAlchemy) related parameters
#
DB_USER = os.getenv("DB_USER", "bkr")
DB_PASSWORD = os.getenv("DB_PASSWORD", "bkr")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "beaker")
DEFAULT_SQLALCHEMY_DATABASE_URI = (
    "postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}".format(
        db_user=DB_USER,
        db_password=DB_PASSWORD,
        db_host=DB_HOST,
        db_port=DB_PORT,
        db_name=DB_NAME,
    )
)
SQLALCHEMY_DATABASE_URI = os.getenv(
    "SQLALCHEMY_DATABASE_URI", DEFAULT_SQLALCHEMY_DATABASE_URI
)

# The following two lines will output the SQL statements
# executed by SQLAlchemy. Useful while debugging and in
# development. Turned off by default
# --------
SQLALCHEMY_ECHO = False
SQLALCHEMY_NATIVE_UNICODE = True
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_MAX_OVERFLOW = 25

# Logging related parameters
LOG_LEVEL = "INFO"
LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s"
