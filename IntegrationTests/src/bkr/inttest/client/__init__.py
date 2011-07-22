
import os
import subprocess
import tempfile
import logging
from bkr.inttest import get_server_base, data_setup

log = logging.getLogger(__name__)

def create_client_config(username, password):
    config = tempfile.NamedTemporaryFile(prefix='bkr-inttest-client-conf-')
    config.write('\n'.join([
        # Kobo wigs out if HUB_URL ends with a trailing slash, not sure why..
        'HUB_URL = "%s"' % get_server_base().rstrip('/'),
        'AUTH_METHOD = "password"',
        'USERNAME = "%s"' % data_setup.ADMIN_USER,
        'PASSWORD = "%s"' % data_setup.ADMIN_PASSWORD
    ]))
    config.flush()
    return config

class ClientError(Exception):

    def __init__(self, command, status, stderr_output):
        Exception.__init__(self, 'Client command %r failed '
                'with exit status %s:\n%s' % (command, status, stderr_output))
        self.stderr_output = stderr_output

# If running against installed beaker-client, BEAKER_CLIENT_COMMAND=bkr should 
# be set in the environment. Otherwise we assume we're in a source checkout and 
# fall back to the run-client.sh script.
client_command = os.environ.get('BEAKER_CLIENT_COMMAND',
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'run-client.sh'))

def run_client(args):
    config_filename = default_client_config.name
    log.debug('Running client %r as %r with BEAKER_CLIENT_CONF=%s',
            client_command, args, config_filename)
    p = subprocess.Popen(args, executable=client_command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ.items() +
                [('BEAKER_CLIENT_CONF', config_filename)]))
    out, err = p.communicate()
    if p.returncode:
        raise ClientError(args, p.returncode, err)
    assert err == '', err
    return out

default_client_config = None

def setup_package():
    global default_client_config
    default_client_config = create_client_config(username=data_setup.ADMIN_USER,
            password=data_setup.ADMIN_PASSWORD)
    log.debug('Default client config written to %s', default_client_config.name)

def teardown_package():
    global default_client_config
    if default_client_config is not None:
        default_client_config.close()
