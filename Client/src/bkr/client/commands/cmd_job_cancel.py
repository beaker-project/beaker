# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr job-cancel: Cancel running Beaker jobs
==========================================

.. program:: bkr job-cancel

Synopsis
--------

:program:`bkr job-cancel` [--msg <message>] [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be cancelled.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Only jobs and recipe sets may be cancelled. It does not make sense to cancel 
individual recipes within a recipe set, or tasks within a recipe, so Beaker 
does not permit this.

Options
-------

.. option:: --msg <message>

   Optionally you can provide a message describing the reason for the 
   cancellation. This message will be recorded against all outstanding tasks in 
   the cancelled recipe set, and will be visible in the Beaker web UI.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Cancel job 1234 with a helpful message::

    bkr job-cancel --msg "Selected wrong distro, resubmitting job" J:1234

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Job_Cancel(BeakerCommand):
    """
    Cancel Jobs/Recipes
    """
    enabled = True

    def options(self):
        self.parser.add_option(
            "--msg",
            default=None,
            help="Optional message to record as to why you cancelled",
        )

        self.parser.usage = "%%prog %s [options] [J:<id> | RS:<id> ...]" % self.normalized_name


    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error('Please specify a taskspec to cancel')
        self.check_taskspec_args(args, permitted_types=['J', 'RS', 'T'])

        msg = kwargs.pop("msg", None)

        self.set_hub(**kwargs)
        for task in args:
            self.hub.taskactions.stop(task, 'cancel', msg)
            print('Cancelled %s' % task)
