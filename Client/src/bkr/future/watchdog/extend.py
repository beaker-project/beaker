# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr watchdog extend: Extend Beaker watchdogs time
==================================================

.. program:: bkr watchdog extend

Synopsis
--------

:program:`bkr watchdog extend` [:option:`--by` <seconds>] [*options*]

Description
-----------

Extends all the watchdog times that are active.

Options
-------

.. option:: --by <seconds>

   Extend the watchdogs by <seconds>. Default is 7200.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Extend all the active watchdogs for 1 hour::

    bkr watchdog extend --by=3600

See also
--------

:manpage:`bkr(1)`
"""

import click

from bkr.future.api import pass_api


@click.command("extend")
@click.option(
    "--by", default=7200, type=int, help="Time in seconds to extend the watchdog by."
)
@pass_api
def extend(api, by: int):
    """Extend Beaker watchdogs time."""
    api.post("watchdogs", json={"time": by})
    click.echo("All watchdogs have been updated.")
