# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr distros-tag: Tag Beaker distros
===================================

.. program:: bkr distros-tag

Synopsis
--------

:program:`bkr distros-tag` [*options*] :option:`--name` <name> <tag>

Description
-----------

Applies the given tag to all matching distros in Beaker. Prints to stdout 
a list of the distros which were tagged.

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

Tags all RHEL8.0.0 nightly trees from a particular date with the "INSTALLS" tag::

    bkr distros-tag --name RHEL-8.0.0-20190410% INSTALLS

Notes
-----

This command is only available to Beaker administrators.

See also
--------

:manpage:`bkr-distros-untag(1)`, :manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Distros_Tag(BeakerCommand):
    """
    Tag distros
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <tag>" % self.normalized_name

        self.parser.add_option(
            "--name",
            default=None,
            help="tag by name, use % for wildcard",
        )

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a tag")

        name = kwargs.pop("name", None)
        tag = args[0]
        if not name:
            self.parser.error('If you really want to tag every distro in Beaker, use --name=%')

        self.set_hub(**kwargs)
        distros = self.hub.distros.tag(name, tag)
        print("Tagged the following distros with tag: %s" % tag)
        print("------------------------------------------------------")
        for distro in distros:
            print(distro)
