# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr user delegate add: Add submission delegate
==============================================

.. program:: bkr user delegate add

Synopsis
--------

| :program:`bkr user delegate add` [*options*] <user>

Description
-----------

Modify a Beaker user.

Allows the adding of submission delegates of the currently logged in user.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Add a new submission delegate:

    bkr user delegate add mydelegate

See also
--------

:manpage:`bkr(1)`
"""

import click

from bkr.future.api import pass_api


@click.command("add")
@click.argument("delegate", type=str, required=True)
@pass_api
def add(api, delegate: str):
    """Add submission delegate."""
    username = api.get("users/+self")["user_name"]
    api.post(f"users/{username}/submission-delegates/", json={"user_name": delegate})
    click.echo(f"Submission delegate {delegate} added to account {username}.")
