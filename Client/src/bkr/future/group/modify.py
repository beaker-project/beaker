# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr group modify: Modify a group
================================

.. program:: bkr group modify

Synopsis
--------

| :program:`bkr group modify` [*options*] <group-name>

Description
-----------

Modify an existing group.

Options
-------

.. option:: --display-name

   New display name of the group.

.. option:: --group-name

   New name of the group.

.. option:: --description

   New description of the group.

.. option:: --add-member

   Add a user to the group. This option can be specified multiple
   times to add more than one user to the group. Should a specified
   user fail to be added, all subsequent users are ignored.

.. option:: --remove-member

   Remove a user from the group. This option can be specified multiple
   times to remove more than one user from the group. Should a specified
   user fail to be removed, all subsequent users are ignored.

.. option:: --grant-owner

   Grant group owner permissions to an existing group member.

.. option:: --revoke-owner

   Remove group owner permissions from an existing group owner.

.. option:: --root-password

   Root password for group jobs.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Modify an existing group 'mygroup' with the new display name 'A new group'::

    bkr group modify --display-name="A new group" mygroup

Modify an existing group 'mygroup' with the new display name 'A new group'
and new group name 'mynewgroup'::

    bkr group modify --display-name="A new group" --group-name="mynewgroup" mygroup

Add a user with username 'user1' to the group 'mygroup'::

    bkr group modify --add-member user1 mygroup

Remove an existing group member with username 'user1' from the group 'mygroup'::

    bkr group modify --remove-member user1 mygroup

Add an existing group member with username 'user1' as an owner of group 'mygroup'::

    bkr group modify --grant-owner user1 mygroup

Revoke group owner rights from an existing group owner of group 'mygroup' with username 'user1'::

    bkr group modify --revoke-owner user1 mygroup

See also
--------

:manpage:`bkr(1)`

"""
from typing import Optional
from urllib import parse

import click
from click import ClickException

from bkr.future.api import pass_api


@click.command("modify")
@click.argument("name")
@click.option("--group-name", help="New name of the group")
@click.option("--display-name", help="New display name of the group")
@click.option("--description", help="New description of the group")
@click.option("--add-member", help="Username of the member to be added", multiple=True)
@click.option(
    "--remove-member", help="Username of the member to be removed", multiple=True
)
@click.option(
    "--grant-owner", help="Username of the member to grant owner rights", multiple=True
)
@click.option(
    "--revoke-owner",
    help="Username of the member to revoke owner rights",
    multiple=True,
)
@click.option("--root-password", help="Root password used for group jobs")
@pass_api
def modify(
    api,
    name: str,
    group_name: Optional[str],
    display_name: Optional[str],
    description: Optional[str],
    add_member: tuple,
    remove_member: tuple,
    grant_owner: tuple,
    revoke_owner: tuple,
    root_password: Optional[str],
):
    """Modify an existing group."""
    if not any(
        [
            group_name,
            display_name,
            description,
            add_member,
            remove_member,
            grant_owner,
            revoke_owner,
            root_password,
        ]
    ):
        raise ClickException("Please specify an attribute to modify.")

    members_url = f"groups/{parse.quote(name)}/members/"
    owners_url = f"groups/{parse.quote(name)}/owners/"

    [api.post(members_url, json={"user_name": member}) for member in add_member]
    [api.delete(members_url, params={"user_name": member}) for member in remove_member]
    [api.post(owners_url, json={"user_name": member}) for member in grant_owner]
    [api.delete(owners_url, params={"user_name": member}) for member in revoke_owner]

    group_attrs = {
        "group_name": group_name,
        "display_name": display_name,
        "description": description,
        "root_password": root_password,
    }
    group_attrs = {
        key: value for key, value in group_attrs.items() if value is not None
    }
    if group_attrs:
        api.patch(f"groups/{parse.quote(name)}", json=group_attrs)

    click.echo(f"Group {name} successfully modified.")
