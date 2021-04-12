# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess
import tempfile
import logging
import pipes
import re
from bkr.inttest import get_server_base, data_setup, DatabaseTestCase

log = logging.getLogger(__name__)


class ClientTestCase(DatabaseTestCase):
    pass


def create_client_config(
    username=data_setup.ADMIN_USER,
    password=data_setup.ADMIN_PASSWORD,
    hub_url=None,
    auth_method=u"password",
    cacert=None,
):
    if hub_url is None:
        hub_url = get_server_base()

    cacert_conf = "# CA_CERT ="
    if cacert is not None:
        cacert_conf = 'CA_CERT = "%s"' % cacert

    config = tempfile.NamedTemporaryFile(prefix="bkr-inttest-client-conf-")
    config.write(
        "\n".join(
            [
                'AUTH_METHOD = "%s"' % auth_method,
                'USERNAME = "%s"' % username,
                'PASSWORD = "%s"' % password,
                # Kobo wigs out if HUB_URL ends with a trailing slash, not sure why..
                'HUB_URL = "%s"' % hub_url.rstrip("/"),
                cacert_conf,
            ]
        )
    )

    config.flush()
    return config


class ClientError(Exception):
    def __init__(self, command, status, stderr_output):
        Exception.__init__(
            self,
            "Client command %r failed "
            "with exit status %s:\n%s"
            % (censor_passwords(command), status, stderr_output),
        )
        self.status = status
        self.stderr_output = stderr_output


def censor_passwords(command_args):
    """Returns a joined command as a string with a censored password"""
    return " ".join(
        re.sub(r"(pass.*=).*\b", r"\1***", pipes.quote(arg)) for arg in command_args
    )


# If running against installed beaker-client, BEAKER_CLIENT_COMMAND=bkr should
# be set in the environment. Otherwise we assume we're in a source checkout and
# fall back to the run-client.sh script.
dev_client_command = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "run-client.sh"
)
client_command = os.environ.get("BEAKER_CLIENT_COMMAND", dev_client_command)


def start_client(args, config=None, env=None, extra_env=None, **kwargs):
    if config is None:
        global default_client_config
        config = default_client_config
    log.debug(
        "Starting client %r as BEAKER_CLIENT_CONF=%s %s",
        client_command,
        config.name,
        censor_passwords(args),
    )
    env = dict(env or os.environ)
    env.update(extra_env or {})
    env["PYTHONUNBUFFERED"] = "1"
    env["BEAKER_CLIENT_CONF"] = config.name
    return subprocess.Popen(
        args,
        executable=client_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        **kwargs
    )


def run_client(args, config=None, input=None, **kwargs):
    if input is not None:
        kwargs.setdefault("stdin", subprocess.PIPE)
    p = start_client(args, config, **kwargs)
    out, err = p.communicate(input)
    if p.returncode:
        raise ClientError(args, p.returncode, err)
    assert err == "", err
    return out


default_client_config = None


def setup_package():
    global default_client_config
    default_client_config = create_client_config()
    log.debug("Default client config written to %s", default_client_config.name)


def teardown_package():
    global default_client_config
    if default_client_config is not None:
        default_client_config.close()
