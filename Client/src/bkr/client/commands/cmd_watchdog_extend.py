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

|  :program:`bkr watchdog-extend` [*options*] [<taskspec> | <fqdn>]
|       [:option:`--by` <seconds>]

Description
-----------

Extends the watchdog time for one or more recipes by specifying one
or more <taskspec> arguments or <fqdn> arguments.

The format of the <taskspec> arguments is either R:<recipe_id>
or T:<recipe_task_id>. The <fqdn> arguments are used for specifying
recipes that are running on the systems.

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

Extend the watchdog for recipe 12345 by 1 hour::

    bkr watchdog-extend --by=3600 R:12345

Extend the watchdog for recipe 12345 by 1 hour running on system
system.example.com::

    bkr watchdog-extend --by=3600 system.example.com

See also
--------

:manpage:`bkr(1)`
"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Watchdog_Extend(BeakerCommand):
    """
    Extend Recipe's Watchdog
    """
    enabled = True

    def options(self):
        self.parser.add_option(
            "--by",
            default=7200, type="int",
            help="Time in seconds to extend the watchdog by.",
        )
        self.parser.usage = "%%prog %s [options] [<taskspec> | <fqdn>]..." % self.normalized_name

    def run(self, *args, **kwargs):
        extend_by = kwargs.pop("by", None)
        if not args:
            self.parser.error(
                'Please either specify one or more <taskspec> arguments or system FQDNs')
        taskspecs = []
        systems = []
        for arg in args:
            if ':' in arg:
                taskspecs.append(arg)
            # for back compatibility to support plain task id
            elif arg.isdigit():
                taskspecs.append('T:%s' % arg)
            else:
                systems.append(arg)
        if taskspecs:
            self.check_taskspec_args(taskspecs, permitted_types=['R', 'T'])
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        for s in systems:
            res = requests_session.post('recipes/by-fqdn/%s/watchdog' %
                                        parse.quote(s, ''), json={'kill_time': extend_by})
            res.raise_for_status()

        for t in taskspecs:
            res = requests_session.post('recipes/by-taskspec/%s/watchdog' %
                                        parse.quote(t), json={'kill_time': extend_by})
            res.raise_for_status()
