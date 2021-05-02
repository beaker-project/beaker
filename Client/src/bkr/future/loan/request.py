# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
.. _bkr-loan-request:

bkr loan request: Request a loan for a Beaker system
====================================================

.. program:: bkr loan request

Synopsis
--------

:program:`bkr loan request` [*options*] <fqdn>

Description
-----------

Request a loan for a Beaker system.

The designated user will have full permissions to reserve, provision and
schedule jobs on that system, even if they would not normally have such
access.

While a system is on loan, only the loan recipient and the system owner
will have permission to reserve or otherwise use the system.

Options
-------

.. option:: --comment

   Comment regarding the loan (for example, the reason for it)


Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Temporarily request a user exclusive access to a particular system::

    bkr loan request --comment 'request this server to run some tests' system1.example.com
    # send request to exclusively use the system
    bkr loan grant --recipient jdoe system1.example.com
    # jdoe now has almost exclusive access to use the system
    bkr loan return system1.example.com
    # Either jdoe or a user with permission to loan the system to other users
    # can return the requested loan

See also
--------

:manpage:`bkr(1)`
"""
from typing import Optional
from urllib import parse

import click

from bkr.future.api import pass_api


@click.command("request")
@click.argument("fqdn", type=str, required=True)
@click.option(
    "--comment",
    default=None,
    help="Comment regarding the loan (for example, the reason for it).",
)
@pass_api
def request(api, fqdn: str, comment: Optional[str]):
    """Send a Loan Request to ask for specific system."""
    request_url = "systems/%s/loan-requests/" % parse.quote(fqdn, "")
    data = {"message": comment}
    api.post(request_url, json=data)
    click.echo("Grant requested.")
