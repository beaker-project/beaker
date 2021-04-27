# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr user delegate remove: Remove submission delegate
==============================================

.. program:: bkr user delegate remove

Synopsis
--------

| :program:`bkr user delegate remove` [*options*] <user>

Description
-----------

Modify a Beaker user.

Allows the removing of submission delegates of the currently logged in user.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Remove a new submission delegate:

    bkr user delegate remove mydelegate

See also
--------

:manpage:`bkr(1)`
"""

import click

from bkr.future.api import pass_api


@click.command("remove")
@click.argument("delegate", type=str, required=True)
@pass_api
def remove(api, delegate: str):
    """Remove submission delegate."""
    username = api.get("users/+self")["user_name"]
    api.delete(
        f"users/{username}/submission-delegates/", params={"user_name": delegate}
    )
    click.echo(f"Submission delegate {delegate} removed from account {username}.")
