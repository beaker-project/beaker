# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-watchdog-extend:

bkr watchdog-extend: Extend Beaker watchdog time
================================================

.. program:: bkr watchdog-extend

Synopsis
--------

:program:`bkr watchdog-extend` [:option:`--by` <seconds>] [*options*] <task_id>...

Description
-----------

Extends the watchdog time for one or more recipe-tasks.

Note that the <task_id> arguments are *not* in the same format as the 
<taskspec> argument accepted by other Beaker commands.

Options
-------

.. option:: --by <seconds>

   Extend the watchdog by <seconds>. Default is 7200.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Extend the watchdog for recipe-task 12345 by 1 hour::

    bkr watchdog-extend --by=3600 12345

See also
--------

:manpage:`bkr(1)`
"""

from bkr.client import BeakerCommand
from optparse import OptionValueError

class Watchdog_Extend(BeakerCommand):
    """Extend Task's Watchdog"""
    enabled = True

    def options(self):
        self.parser.add_option(
            "--by",
            default=7200, type="int",
            help="Time in seconds to extend the watchdog by.",
        )

        self.parser.usage = "%%prog %s [options] <task_id>..." % self.normalized_name


    def run(self, *args, **kwargs):
        extend_by = kwargs.pop("by", None)

        if not args:
            self.parser.error('Please specify one or more task ids.')

        self.set_hub(**kwargs)
        for task_id in args:
            print self.hub.recipes.tasks.extend(task_id, extend_by)

