# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
.. _bkr-loan-return:

bkr loan return: Return a current Beaker system loan
====================================================

.. program:: bkr loan return

Synopsis
--------

:program:`bkr loan return` [*options*] <fqdn>

Description
-----------

Returns a Beaker system loan that was previously granted using :program:`bkr
loan grant` or the Beaker web UI).

Options
-------

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

from urllib import parse

import click

from bkr.future.api import pass_api


@click.command("return")
@click.argument("fqdn", type=str, required=True)
@pass_api
def return_grant(api, fqdn: str):
    """Return a current Beaker system loan."""
    return_url = "systems/%s/loans/+current" % parse.quote(fqdn, "")
    data = {"finish": "now"}
    api.patch(return_url, json=data)
    click.echo("Grant returned successfully.")
