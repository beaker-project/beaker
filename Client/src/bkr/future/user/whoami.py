# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later
import json

import click

from bkr.future.api import pass_api


@click.command("whoami")
@pass_api
def whoami(api):
    """Show current identity"""

    attributes: dict = api.get("users/+self")

    result: dict = {
        "username": attributes["user_name"],
        "email_address": attributes["email_address"],
    }
    if attributes.get("proxied_by_user"):
        result["proxied_by_username"] = attributes["proxied_by_user"]["user_name"]
    click.echo(json.dumps(result))
