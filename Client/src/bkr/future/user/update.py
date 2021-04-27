# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr user update: Update user preferences
========================================

.. program:: bkr user update

Synopsis
--------

| :program:`bkr user update` [*options*]
|       [:option:`--email` <email_address> ...]

Description
-----------

Update user preferences

Options
-------

.. option:: --email <email_address>

   Update user's email address

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Update user's email address

    bkr user update --email=foobar@example.com

See also
--------

:manpage:`bkr(1)`
"""
from typing import Optional

import click

from bkr.future.api import pass_api


@click.command("update")
@click.option(
    "--email",
    default=None,
    type=str,
    help="New email address.",
)
@pass_api
def update(api, email: Optional[str]):
    """Update user preferences."""
    if not email:
        click.echo("Nothing to update.")
        return
    username = api.get("users/+self")["user_name"]
    payload = {"email_address": email}
    api.patch(f"users/{username}", json=payload)
    click.echo("Preferences updated.")
