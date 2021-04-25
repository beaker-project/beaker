# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr group list: List groups
===========================

.. program:: bkr group list

Synopsis
--------

| :program:`bkr group list`
|       [:option:`--owner` <user>]
|       [:option:`--limit` <number>]

Description
-----------

Lists groups or groups owned by the given user.

Options
-------

.. option:: --owner <username>

   List groups owned by <username>.

.. option:: --limit <number>

   Return at most <number> groups. The default is 50.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List all groups which are owned by the user ``test``::

    bkr group list --owner test

"""

import click
from click import ClickException

from bkr.future.api import pass_api


@click.command("list")
@click.option("--owner", help="List groups owned by owner USERNAME.")
@click.option("--limit", default=50, help="Limit number of results.", show_default=True)
@pass_api
def list_groups(api, owner, limit):
    """Lists groups or groups owned by the given user."""

    params = {"page_size": limit}
    if owner:
        params["q"] = "owner.user_name:%s" % owner

    attributes = api.get("groups/", params=params)
    groups = attributes["entries"]

    if not groups:
        raise ClickException("Nothing Matches\n")

    for group in groups:
        click.echo((group["group_name"]))
