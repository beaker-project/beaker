# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr distro-trees-list: List Beaker distro trees
===============================================

.. program:: bkr distro-trees-list

Synopsis
--------

| :program:`bkr distro-trees-list` [*options*]
|       [:option:`--tag` <tag>] [:option:`--name` <name>] [:option:`--treepath` <url>] [:option:`--family` <family>]
        [:option:`--arch` <arch>] [:option:`--distro-id` <distroid>] [:option:`--distro-tree-id` <distrotreeid>]
|       [:option:`--limit` <number>] [:option:`--format` <format>]

Description
-----------

Prints to stdout the details of all matching Beaker distro trees.

Options
-------

.. option:: --tag <tag>

   Limit to distros which have been tagged in Beaker with <tag>.

.. option:: --name <name>

   Limit to distros with the given name. <name> is interpreted as a SQL LIKE 
   pattern (the % character matches any substring).

.. option:: --treepath <url>

   Limit to distro trees with the given tree path. <url> is interpreted as 
   a SQL LIKE pattern (the % character matches any substring).

.. option:: --labcontroller <fqdn>

   Limit to distro trees which are available on the given lab controller. 
   <fqdn> is interpreted as a SQL LIKE pattern (the % character matches any 
   substring).

.. option:: --family <family>

   Limit to distros of the given family (major version), for example 
   ``RedHatEnterpriseLinuxServer8``.

.. option:: --arch <arch>

   Limit to distro trees for the given arch.

.. option:: --distro-id <distroid>

   Limit to distro trees for the given distro id.

.. option:: --distro-tree-id <distrotreeid>

   Limit to distro trees for the given distro tree id.

.. option:: --xml-filter <xml>

   Limit to distro trees which match the given XML filter criteria. Supports 
   the same criteria as inside the ``<distroRequires/>`` element in Beaker job 
   XML.

.. option:: --limit <number>

   Return at most <number> distro trees.

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

List details of all RHEL 8.0.0 nightly trees from a particular date::

    bkr distro-trees-list --name "RHEL-8.0.0-20190410%"

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-distros-list(1)`
"""

from __future__ import print_function

import json
import sys

from bkr.client import BeakerCommand


class Distro_Trees_List(BeakerCommand):
    """
    List distro trees
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
            "--treepath",
            default=None,
            help="filter by treepath, use % for wildcard",
        )
        self.parser.add_option(
            "--labcontroller",
            default=None,
            help="filter by lab controller, use % for wildcard",
        )
        self.parser.add_option(
            "--family",
            default=None,
            help="filter by family",
        )
        self.parser.add_option(
            "--arch",
            default=None,
            help="filter by arch",
        )
        self.parser.add_option(
            "--distro-id",
            default=None,
            help="filter by Distro ID",
        )
        self.parser.add_option(
            "--distro-tree-id",
            default=None,
            help="filter by Distro Tree ID",
        )
        self.parser.add_option(
            '--xml-filter', default=None, metavar='XML',
            help='filter by XML criteria, as in <distroRequires/>',
        )

    def run(self, *args, **kwargs):
        filter = dict( limit    = kwargs.pop("limit", None),
                       name     = kwargs.pop("name", None),
                       treepath = kwargs.pop("treepath", None),
                       labcontroller = kwargs.pop("labcontroller", None),
                       family   = kwargs.pop("family", None),
                       arch     = kwargs.pop("arch", None),
                       tags     = kwargs.pop("tag", []),
                       distro_id = kwargs.pop("distro_id", None),
                       distro_tree_id = kwargs.pop("distro_tree_id", None),
                       xml      = kwargs.pop('xml_filter', None),
                     )
        format = kwargs['format']

        self.set_hub(**kwargs)
        distro_trees = self.hub.distrotrees.filter(filter)
        if format == 'json':
            print(json.dumps(distro_trees, indent=4))
        elif format == 'tabular':
            if distro_trees:
                print("-" * 70)
                for dt in distro_trees:
                    print("       ID: %s" % dt['distro_tree_id'])
                    print("     Name: %-34.34s Arch: %s" % (dt['distro_name'], dt['arch']))
                    print("OSVersion: %-34.34s Variant: %s" % (
                        dt['distro_osversion'], dt['variant']))
                    print("     Tags: %s" % ", ".join(dt['distro_tags']))
                    print()
                    print("  Lab controller/URLs:")
                    for labc, url in dt['available']:
                        print("     %-32s: %s" % (labc, url))
                    print("-" * 70)
            else:
                sys.stderr.write("Nothing Matches\n")
        if not distro_trees:
            sys.exit(1)
