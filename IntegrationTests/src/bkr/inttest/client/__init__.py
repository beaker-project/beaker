
import os
import subprocess
import tempfile
import logging
from bkr.inttest import get_server_base, data_setup

log = logging.getLogger(__name__)

def create_client_config(username=data_setup.ADMIN_USER,
    password=data_setup.ADMIN_PASSWORD, hub_url=None,
    qpid_broker='localhost',qpid_krb=False):
    if hub_url is None:
        hub_url = get_server_base()
    config = tempfile.NamedTemporaryFile(prefix='bkr-inttest-client-conf-')
    config.write('\n'.join([
        # Kobo wigs out if HUB_URL ends with a trailing slash, not sure why..
        'HUB_URL = "%s"' % hub_url.rstrip('/'),
        'AUTH_METHOD = "password"',
        'USERNAME = "%s"' % username,
        'PASSWORD = "%s"' % password,
        'QPID_TOPIC_EXCHANGE = "amqp.topic"',
        'QPID_HEADERS_EXCHANGE = "amqp.headers"',
        'QPID_BROKER = "%s"' % qpid_broker,
        'QPID_KRB = %s' % qpid_krb,
    ]))
    config.flush()
    return config

class ClientError(Exception):

    def __init__(self, command, status, stderr_output):
        Exception.__init__(self, 'Client command %r failed '
                'with exit status %s:\n%s' % (command, status, stderr_output))
        self.status = status
        self.stderr_output = stderr_output

# If running against installed beaker-client, BEAKER_CLIENT_COMMAND=bkr should 
# be set in the environment. Otherwise we assume we're in a source checkout and 
# fall back to the run-client.sh script.
client_command = os.environ.get('BEAKER_CLIENT_COMMAND',
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'run-client.sh'))

def start_client(args, config=None, **kwargs):
    if config is None:
        global default_client_config
        config = default_client_config
    log.debug('Starting client %r as %r with BEAKER_CLIENT_CONF=%s',
            client_command, args, config.name)
    return subprocess.Popen(args, executable=client_command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ.items() +
                [('PYTHONUNBUFFERED', '1'),
                 ('BEAKER_CLIENT_CONF', config.name)]),
            **kwargs)

def run_client(args, config=None, input=None, **kwargs):
    if input is not None:
        kwargs.setdefault('stdin', subprocess.PIPE)
    p = start_client(args, config, **kwargs)
    out, err = p.communicate(input)
    if p.returncode:
        raise ClientError(args, p.returncode, err)
    assert err == '', err
    return out

default_client_config = None

def setup_package():
    global default_client_config
    default_client_config = create_client_config()
    log.debug('Default client config written to %s', default_client_config.name)

def teardown_package():
    global default_client_config
    if default_client_config is not None:
        default_client_config.close()
