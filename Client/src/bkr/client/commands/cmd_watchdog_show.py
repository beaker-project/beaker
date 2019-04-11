# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr watchdog-show: Show time remaining on Beaker watchdogs
==========================================================

.. program:: bkr watchdog-show

Synopsis
--------

:program:`bkr watchdog-show` [*options*] <task_id>...

Description
-----------

Prints to stdout the watchdog time remaining for one or more recipe-tasks. The 
format of each line of output is ``<task_id>: <seconds>``.

Note that the <task_id> arguments are *not* in the same format as the 
<taskspec> argument accepted by other Beaker commands.

If the task does not have a watchdog, 'N/A' will be printed.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Show the number of seconds remaining on the watchdog for recipe-task 12345::

    bkr watchdog-show 12345

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Watchdog_Show(BeakerCommand):
    """
    Display Task's Watchdog
    """
    enabled = True
    requires_login = False

    def options(self):
        self.parser.usage = "%%prog %s [options] <task_id>..." % self.normalized_name


    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)
        for task_id in args:
            seconds_left = self.hub.recipes.tasks.watchdog(task_id)
            print("%s: %s" % (task_id, seconds_left or 'N/A'))

