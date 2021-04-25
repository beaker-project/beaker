# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr group create: Create a group
================================

.. program:: bkr group create

Synopsis
--------

| :program:`bkr group create` [*options*] <group-name>

Description
-----------

Create a new group with the specified name, display name and root password.

Options
-------

.. option:: --ldap

   Populate the members from an LDAP group, specified by <group-name>.

.. option:: --display-name

   Display name of the group.

.. option:: --description

   Description of the group.

.. option:: --root-password

   Root password for group jobs.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Create a group with the following group name, display name, and root password: 'mygroup',
'My Group', and 'd3c0yz3d' respectively::

    bkr group create --display-name="My Group" --root-password="d3c0yz3d" mygroup

See also
--------

:manpage:`bkr(1)`
"""

import click

from bkr.future.api import pass_api


@click.command("create")
@click.argument("group_name")
@click.option("--display-name", help="Display name of the group.")
@click.option("--description", help="Description of the group.")
@click.option("--ldap", is_flag=True, help="Create an LDAP group.")
@click.option("--root-password", help="Root password used for group jobs.")
@pass_api
def create(api, group_name, display_name, description, ldap, root_password):
    """Create a new group with specified attributes."""
    if not display_name:
        display_name = group_name

    api.post(
        "groups/",
        json=dict(
            group_name=group_name,
            root_password=root_password,
            display_name=display_name,
            description=description,
            ldap=ldap,
        ),
    )
    click.echo(f"Group created: {group_name}.")
