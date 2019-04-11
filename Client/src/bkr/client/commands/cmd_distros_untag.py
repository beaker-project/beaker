# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr distros-untag: Untag Beaker distros
=======================================

.. program:: bkr distros-untag

Synopsis
--------

:program:`bkr distros-untag` [*options*] :option:`--name` <name> <tag>

Description
-----------

Removes the given tag from all matching distros in Beaker. Prints to stdout 
a list of the distros which were untagged.

Options
-------

.. option:: --name <name>

   Limit to distros with the given name. <name> is interpreted as a SQL LIKE 
   pattern (the % character matches any substring).

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Removes the "STABLE" tag from all RHEL 8.0.0 nightly trees from a particular date::

    bkr distros-untag --name RHEL-8.0.0-20190410% STABLE

Notes
-----

This command is only available to Beaker administrators.

See also
--------

:manpage:`bkr-distros-tag(1)`, :manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Distros_Untag(BeakerCommand):
    """
    Untag distros
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <tag>" % self.normalized_name

        self.parser.add_option(
            "--name",
            default=None,
            help="untag by name, use % for wildcard",
        )
        self.parser.add_option(
            "--arch",
            default=None,
            help="untag by arch",
        )

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a tag")

        name = kwargs.pop("name", None)
        tag = args[0]
        if not name:
            self.parser.error('If you really want to untag every distro in Beaker, use --name=%')

        self.set_hub(**kwargs)
        distros = self.hub.distros.untag(name, tag)
        print("Removed Tag %s from the following distros:" % tag)
        print("------------------------------------------------------")
        for distro in distros:
            print(distro)
