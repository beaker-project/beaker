# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
.. _bkr-loan-grant:

bkr loan grant: Grant a loan for a Beaker system
================================================

.. program:: bkr loan grant

Synopsis
--------

:program:`bkr loan grant` [*options*] <fqdn>

Description
-----------

Grant a loan for a Beaker system.

The designated user will have full permissions to reserve, provision and
schedule jobs on that system, even if they would not normally have such
access.

While a system is on loan, only the loan recipient and the system owner
will have permission to reserve or otherwise use the system.

Options
-------

.. option:: --recipient

   Username of the loan recipient (defaults to the user issuing the command)

.. option:: --comment

   Comment regarding the loan (for example, the reason for it)


Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Temporarily grant a user exclusive access to a particular system::

    bkr loan grant --recipient jdoe system1.example.invalid
    # jdoe now has almost exclusive access to use the system
    bkr loan return system1.example.invalid
    # Either jdoe or a user with permission to loan the system to other users
    # can return the granted loan

See also
--------

:manpage:`bkr(1)`
"""

from typing import Optional
from urllib import parse

import click

from bkr.future.api import pass_api


@click.command("grant")
@click.argument("fqdn", type=str, required=True)
@click.option(
    "--recipient",
    default=None,
    help="Username of the loan recipient (defaults to the user issuing the command).",
)
@click.option(
    "--comment",
    default=None,
    help="Comment regarding the loan (for example, the reason for it).",
)
@pass_api
def grant(api, fqdn: str, recipient: Optional[str], comment: Optional[str]):
    """Grant a loan for a Beaker system."""
    grant_url = "systems/%s/loans/" % parse.quote(fqdn, "")
    data = {"recipient": recipient, "comment": comment}
    api.post(grant_url, json=data)
    click.echo("Grant created successfully.")
