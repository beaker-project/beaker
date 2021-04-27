# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

"""
bkr watchdog list: Show time remaining on Beaker watchdogs
==========================================================

.. program:: bkr watchdog list

Synopsis
--------

:program:`bkr watchdog list` [*options*] <taskspec>...

Description
-----------

Prints to stdout the watchdog time remaining for one or more recipe-tasks. The
format of each line of output is ``<task_id>: <seconds>``.

The format of the <taskspec> arguments is T:<recipe_task_id>.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Show the number of seconds remaining on the watchdog for recipe-task T:12345::

    bkr watchdog-show T:12345

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


@click.command("list")
@click.argument(
    "task_spec",
    nargs=-1,
    type=TaskSpecParamType([TaskSpecType.T]),
)
@pass_api
def list_watchdog(api, task_spec: List[TaskSpec]):
    """Show time remaining on Beaker watchdogs."""
    for item in task_spec:
        payload = api.get(
            "recipes/by-taskspec/%s/watchdog" % parse.quote(str(item).encode()),
        )
        click.echo(f"{item}:{payload['seconds']}")
