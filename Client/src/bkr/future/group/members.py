# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr group members: List members of a group
==========================================

.. program:: bkr group members

Synopsis
--------

| :program:`bkr group members` [*options*] <group-name>

Description
-----------

List the members of an existing group.

Options
-------

.. option:: --format <format>

   Display results in the given format, either ``LIST`` or ``JSON``.
   The `LIST`` format lists one user per line and is useful to be fed as input
   to other command line utilities. The default format is ``JSON``, which
   returns the users as a JSON array.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

:manpage:`bkr(1)`

"""

import json
from urllib import parse

import click

from bkr.future.api import pass_api


@click.command("members")
@click.argument("group_name")
@click.option(
    "--format",
    "usr_format",
    type=click.Choice(["LIST", "JSON"]),
    default="JSON",
    help="Results display format",
    show_default=True,
)
@pass_api
def members(api, group_name, usr_format: str):
    """List the members of an existing group."""

    res = api.get("groups/%s" % parse.quote(group_name))
    bkr_members = []

    for u in res["members"]:
        user = dict()
        user["username"] = u["user_name"]
        user["email"] = u["email_address"]
        user["owner"] = u in res["owners"]
        bkr_members.append(user)

    if usr_format.lower() == "json":
        click.echo(json.dumps(bkr_members))
    else:
        click.echo(
            "\n".join(
                [
                    f"{m['username']} {m['email']} {'Owner' if m['owner'] else 'Member'}"
                    for m in bkr_members
                ]
            )
        )
