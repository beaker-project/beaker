import pkg_resources
from turbogears.config import update_config
from turbogears.database import metadata, get_engine

def setup_package():
    update_config(configfile=pkg_resources. \
        resource_filename('bkr.server.tests', 'unit-test.cfg'),
        modulename='bkr.server.config')
    get_engine()
    metadata.create_all()
