# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import sys
from typing import Optional

import click
import requests

from bkr.common import __version__
from bkr.future.api import ClientBeakerAPI
from bkr.future.config import read_user_override
from bkr.future.group import group
from bkr.future.job import job
from bkr.future.labcontroller import labcontroller
from bkr.future.loan import loan
from bkr.future.pool import pool
from bkr.future.system import system
from bkr.future.task import task
from bkr.future.user import user
from bkr.future.watchdog import watchdog
from bkr.future.user.whoami import whoami
from bkr.future.workflow import workflow

logger = logging.getLogger("bkr")


@click.group("bkr")
@click.option("-d", "--debug", is_flag=True, help="Enable debug output.")
@click.option(
    "--api",
    default=None,
    help="Connect to Beaker server at URL (overrides config file).",
)
@click.option(
    "--username",
    default=None,
    help="Use USERNAME for basic authentication (overrides config file).",
)
@click.option(
    "--password",
    default=None,
    help="Use PASSWORD for basic authentication (overrides config file).",
    hide_input=True,
)
@click.option(
    "-k",
    "--insecure",
    flag_value=False,
    default=None,
    help="Skip SSL certificate validity checks.",
)
@click.option("--proxy-user", default=None, help="TBD")
@click.version_option(version=__version__, message="%(version)s")
@click.pass_context
def base(
    ctx: click.Context,
    debug: bool,
    api: Optional[str],
    username: Optional[str],
    password: Optional[str],
    insecure: Optional[bool],
    proxy_user: Optional[str],
):
    """Beaker Client"""
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    cli_configuration = {
        "HUB_URL": api,
        "USERNAME": username,
        "PASSWORD": password,
        "SSL_VERIFY": insecure,
        "PROXY_USER": proxy_user,
    }
    cli_configuration = {
        option: value
        for option, value in cli_configuration.items()
        if value is not None
    }
    logger.debug(cli_configuration)

    configuration = read_user_override(cli_configuration)
    ctx.obj = ClientBeakerAPI.from_config(configuration)

    logger.debug(f"Beaker client {__version__} is being used.")


base.add_command(group)
base.add_command(job)
base.add_command(labcontroller)
base.add_command(loan)
base.add_command(pool)
base.add_command(system)
base.add_command(task)
base.add_command(user)
base.add_command(watchdog)
base.add_command(workflow)
base.add_command(whoami)

if __name__ == "__main__":
    try:
        base()
    except requests.exceptions.HTTPError as e:
        response: requests.Response = e.response
        click.echo(f"[{response.status_code}] {response.text}")
        sys.exit(1)
