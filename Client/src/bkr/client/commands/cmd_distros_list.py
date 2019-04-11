# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr distros-list: List Beaker distros
=====================================

.. program:: bkr distros-list

Synopsis
--------

| :program:`bkr distros-list` [*options*]
|       [:option:`--tag` <tag>] [:option:`--name` <name>] [:option:`--family` <family>]
|       [:option:`--distro-id` <distroid>] [:option:`--limit` <number>] [:option:`--format` <format>]

Description
-----------

Prints to stdout the details of all matching Beaker distros.

Options
-------

.. option:: --tag <tag>

   Limit to distros which have been tagged in Beaker with <tag>.

.. option:: --name <name>

   Limit to distros with the given name. <name> is interpreted as a SQL LIKE 
   pattern (the % character matches any substring).

.. option:: --family <family>

   Limit to distros of the given family (major version), for example 
   ``RedHatEnterpriseLinuxServer5``.

.. option:: --distro-id <distroid>

   Limit to distros of the given distroid.

.. option:: --limit <number>

   Return at most <number> distros.

.. option:: --format <format>

   Display results in the given format, either ``tabular`` or ``json``.
   The ``tabular`` format is verbose and intended for human consumption, 
   whereas the ``json`` format is machine-readable. The default is ``tabular``.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.
If no distros match the given criteria this is considered to be an error, and 
the exit status will be 1.

Examples
--------

List details of all RHEL7 distros with the RELEASED tag::

    bkr distros-list --family RedHatEnterpriseLinux7 --tag RELEASED

History
-------

Prior to version 0.9, this command also accepted :option:`--treepath <bkr distro-trees-list --treepath>`, 
:option:`--labcontroller <bkr distro-trees-list --labcontroller>`, and :option:`--arch <bkr distro-trees-list --arch>`
filter options. Use :program:`bkr distro-trees-list` instead.

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-distro-trees-list(1)`
"""

from __future__ import print_function

import json
import sys

from bkr.client import BeakerCommand


class Distros_List(BeakerCommand):
    """
    List distros
    """
    enabled = True
    requires_login = False

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

        self.parser.add_option(
            "--limit",
            default=10,
            type=int,
            help="Limit results to this many (default 10)",
        )
        self.parser.add_option(
            '--format',
            type='choice',
            choices=['tabular', 'json'],
            default='tabular',
            help='Display results in this format: tabular, json [default: %default]',
        )
        self.parser.add_option(
            "--tag",
            action="append",
            help="filter by tag",
        )
        self.parser.add_option(
            "--name",
            default=None,
            help="filter by name, use % for wildcard",
        )
        self.parser.add_option(
            "--family",
            default=None,
            help="filter by family",
        )
        self.parser.add_option(
            "--distro-id",
            default=None,
            help="filter by distro id",
        )

    def run(self, *args, **kwargs):
        filter = dict( limit    = kwargs.pop("limit", None),
                       name     = kwargs.pop("name", None),
                       family   = kwargs.pop("family", None),
                       tags     = kwargs.pop("tag", []),
                       distroid = kwargs.pop("distro_id", None),
                     )
        format = kwargs['format']

        self.set_hub(**kwargs)
        distros = self.hub.distros.filter(filter)
        if format == 'json':
            print(json.dumps(distros, indent=4))
        elif format == 'tabular':
            if distros:
                print("-" * 70)
                for distro in distros:
                    print("       ID: %s" % distro['distro_id'])
                    print("     Name: %s" % distro['distro_name'])
                    print("OSVersion: %s" % distro['distro_version'])
                    print("     Tags: %s" % ", ".join(distro['distro_tags']))
                    print("-" * 70)
            else:
                sys.stderr.write("Nothing Matches\n")
        if not distros:
            sys.exit(1)
