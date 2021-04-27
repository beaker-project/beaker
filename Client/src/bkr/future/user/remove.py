# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr user remove: Remove user accounts
========================================

.. program:: bkr user remove

Synopsis
--------

| :program:`bkr user remove` <user>...

Description
-----------

Removes a Beaker user account.

When the account is removed:

* it is removed from all groups and access policies
* any running jobs owned by the account are cancelled
* any systems reserved by or loaned to the account are returned
* any systems owned by the account are transferred to the admin running this
  command, or some other user if specified using :option:`--new-owner`
* the account is disabled for further login

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Options
-------

.. option:: --new-owner <username>

   Transfers the ownership of any systems currently owned by the closed
   accounts to USERNAME.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Close the accounts of users, user1 and user2::

    bkr user remove user1 user2

Close the account of user1 and assign their systems to user2::

    bkr user remove --new-owner=user2 user1

See also
--------

:manpage:`bkr(1)`
"""

from typing import Optional, List

import click

from bkr.future.api import pass_api


@click.command("remove")
@click.argument("username", nargs=-1, type=str)
@click.option(
    "--new-owner",
    default=None,
    type=str,
    help="Transfers the ownership of any systems currently owned by the closed accounts to USERNAME.",
)
@pass_api
def remove(api, username: List[str], new_owner: Optional[str]):
    """Remove user accounts."""
    new_owner: str = new_owner if new_owner else api.get("users/+self")["user_name"]
    payload: dict = {"removed": "now", "new_owner": new_owner}
    [api.patch(f"users/{user}", json=payload) for user in username]
    click.echo(
        f"Account{'s' if len(username) > 1 else ''} removed. New owner is {new_owner}."
    )
