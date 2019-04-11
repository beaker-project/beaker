# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr watchdogs-extend: Extend Beaker watchdogs time
==================================================

.. program:: bkr watchdogs-extend

Synopsis
--------

:program:`bkr watchdogs-extend` [:option:`--by` <seconds>] [*options*]

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

    bkr watchdogs-extend --by=3600

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Watchdogs_Extend(BeakerCommand):
    """
    Extend the Watchdog for all Tasks
    """
    enabled = True

    def options(self):
        self.parser.add_option(
            "--by",
            default=7200, type="int",
            help="Time in seconds to extend the watchdog by.",
        )

        self.parser.usage = "%%prog %s [options]" % self.normalized_name

    def run(self, *args, **kwargs):
        extend_by = kwargs.pop("by", None)

        self.set_hub(**kwargs)
        print(self.hub.watchdogs.extend(extend_by))
