
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess
import tempfile
import logging
from bkr.inttest import get_server_base, data_setup, DatabaseTestCase
from bkr.client import wizard

log = logging.getLogger(__name__)

class ClientTestCase(DatabaseTestCase): pass

def create_client_config(username=data_setup.ADMIN_USER,
                         password=data_setup.ADMIN_PASSWORD,
                         hub_url=None,
                         auth_method=u'password',
                         qpid_broker='localhost',
                         qpid_krb=False,
                         cacert=None):
    if hub_url is None:
        hub_url = get_server_base()

    cacert_conf = '# CA_CERT ='
    if cacert is not None:
        cacert_conf = 'CA_CERT = "%s"' % cacert

    config = tempfile.NamedTemporaryFile(prefix='bkr-inttest-client-conf-')
    config.write('\n'.join([
                'AUTH_METHOD = "%s"' % auth_method,
                'USERNAME = "%s"' % username,
                'PASSWORD = "%s"' % password,
                # Kobo wigs out if HUB_URL ends with a trailing slash, not sure why..
                'HUB_URL = "%s"' % hub_url.rstrip('/'),
                'QPID_TOPIC_EXCHANGE = "amqp.topic"',
                'QPID_HEADERS_EXCHANGE = "amqp.headers"',
                'QPID_BROKER = "%s"' % qpid_broker,
                'QPID_KRB = %s' % qpid_krb,
                cacert_conf
        ]))

    config.flush()
    return config

def create_wizard_config():
    config = tempfile.NamedTemporaryFile(prefix='bkr-inttest-wizard-conf-')
    config.write(wizard.PreferencesTemplate)
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
dev_client_command = os.path.join(os.path.dirname(__file__),
                                  '..', '..', '..', '..', 'run-client.sh')
client_command = os.environ.get('BEAKER_CLIENT_COMMAND', dev_client_command)

def start_client(args, config=None, env=None, extra_env=None, **kwargs):
    if config is None:
        global default_client_config
        config = default_client_config
    log.debug('Starting client %r as %r with BEAKER_CLIENT_CONF=%s',
            client_command, args, config.name)
    env = dict(env or os.environ)
    env.update(extra_env or {})
    env['PYTHONUNBUFFERED'] = '1'
    env['BEAKER_CLIENT_CONF'] = config.name
    return subprocess.Popen(args, executable=client_command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env,
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


dev_wizard_command = os.path.join(os.path.dirname(__file__),
                                  '..', '..', '..', '..', 'run-wizard.sh')
wizard_command = os.environ.get('BEAKER_WIZARD_COMMAND', dev_wizard_command)

def start_wizard(args, config=None, env=None, **kwargs):
    if config is None:
        global default_wizard_config
        config = default_wizard_config
    log.debug('Starting beaker-wizard %r as %r in directory %s',
            wizard_command, args, kwargs.get('cwd', '.'))
    env = dict(env or os.environ)
    env['PYTHONUNBUFFERED'] = '1'
    env['BEAKER_WIZARD_CONF'] = config.name
    return subprocess.Popen(args,
                            executable=wizard_command,
                            stdout=subprocess.PIPE,
                            stdin=open('/dev/null'),
                            stderr=subprocess.PIPE,
                            env=env,
                            **kwargs)

def run_wizard(args, **kwargs):
    p = start_wizard(args, **kwargs)
    # Poor man's output rate limiting. Strictly we should be reading from 
    # stdout and stderr concurrently in order to avoid deadlocks.
    max_output = 10240
    out = p.stdout.read(max_output)
    if len(out) == max_output:
        raise RuntimeError('Output size limit exceeded when invoking %r:\n%s'
                % (args, out))
    err = p.stderr.read(max_output)
    if len(err) == max_output:
        raise RuntimeError('Stderr size limit exceeded when invoking %r:\n%s'
                % (args, err))
    p.wait()
    if p.returncode:
        raise ClientError(args, p.returncode, err)
    assert err == '', err
    return out

def setup_package():
    global default_client_config
    default_client_config = create_client_config()
    log.debug('Default client config written to %s', default_client_config.name)
    global default_wizard_config
    default_wizard_config = create_wizard_config()
    log.debug('Default wizard config written to %s', default_wizard_config.name)

def teardown_package():
    global default_client_config
    if default_client_config is not None:
        default_client_config.close()
    global default_wizard_config
    if default_wizard_config is not None:
        default_wizard_config.close()
