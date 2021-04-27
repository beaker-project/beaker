# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
.. _bkr-watchdog-set:

bkr watchdog set: Set Beaker watchdog time
================================================

.. program:: bkr watchdog set

Synopsis
--------

|  :program:`bkr watchdog set` [*options*] <taskspec>
|       [:option:`--by` <seconds>]

Description
-----------

Sets the watchdog time for one or more recipes by specifying one
or more <taskspec> arguments.

The format of the <taskspec> arguments is either R:<recipe_id>
or T:<recipe_task_id>.

Options
-------

.. option:: --by <seconds>

   Set the watchdog by <seconds>. Default is 7200.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Set the watchdog for recipe 12345 by 1 hour::

    bkr watchdog set --by=3600 R:12345

See also
--------

:manpage:`bkr(1)`
"""
from typing import List
from urllib import parse

import click

from bkr.future.api import pass_api
from bkr.future.taskspec import TaskSpecType, TaskSpec
from bkr.future.param_types import TaskSpecParamType


@click.command("set")
@click.argument(
    "task_spec",
    nargs=-1,
    type=TaskSpecParamType([TaskSpecType.R, TaskSpecType.T]),
)
@click.option(
    "--time", default=7200, type=int, help="New watchdog time in seconds."
)
@pass_api
def set_watchdog(api, task_spec: List[TaskSpec], time: int):
    """Set Beaker watchdog time"""
    for item in task_spec:
        api.post(
            "recipes/by-taskspec/%s/watchdog" % parse.quote(str(item).encode()),
            json={"kill_time": time},
        )
    click.echo("All watchdogs have been updated.")
