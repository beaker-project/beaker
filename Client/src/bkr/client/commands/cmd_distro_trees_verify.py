# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr distro-trees-verify: Check Beaker distro trees for problems
===============================================================

.. program:: bkr distro-trees-verify

Synopsis
--------

| :program:`bkr distro-trees-verify` [*options*]
|       [:option:`--tag` <tag>] [:option:`--name` <name>] [:option:`--treepath` <url>] [:option:`--family` <family>] [:option:`--arch` <arch>]
|       [--broken] [:option:`--limit` <number>]

Description
-----------

Prints to stdout a list of matching distro trees in Beaker, along with a list 
of labs (if any) which do not have the tree.

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

.. option:: --family <family>

   Limit to distros of the given family (major version), for example 
   ``RedHatEnterpriseLinuxServer8``.

.. option:: --arch <arch>

   Limit to distro trees for the given arch.

.. option:: --broken

   Limit to distro trees which are not present in every lab.

.. option:: --limit <number>

   Return at most <number> distros.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.
If no distros match the given criteria this is considered to be an error, and 
the exit status will be 1.

History
-------

Prior to version 0.9, this command was called :program:`bkr distros-verify`.

See also
--------

:manpage:`bkr-distro-trees-list(1)`, :manpage:`bkr(1)`
"""

from __future__ import print_function

import sys

from bkr.client import BeakerCommand


class Distro_Trees_Verify(BeakerCommand):
    """
    Verify distro trees
    """
    enabled = True
    requires_login = False

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

        self.parser.add_option(
            "--broken",
            action="store_true",
            help="Only show distros not synced on every lab",
        )
        self.parser.add_option(
            "--limit",
            default=None,
            help="Limit results to this many",
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
            "--family",
            default=None,
            help="filter by family",
        )
        self.parser.add_option(
            "--arch",
            default=None,
            help="filter by arch",
        )

    def run(self, *args, **kwargs):
        onlybroken = kwargs.pop("broken", False)
        filter = dict( limit    = kwargs.pop("limit", None),
                       name     = kwargs.pop("name", None),
                       treepath = kwargs.pop("treepath", None),
                       family   = kwargs.pop("family", None),
                       arch     = kwargs.pop("arch", None),
                       tags     = kwargs.pop("tag", []),
                     )

        self.set_hub(**kwargs)
        lab_controllers = set(self.hub.lab_controllers())
        trees = self.hub.distrotrees.filter(filter)
        if trees:
            for tree in trees:
                available_lcs = set(lc for lc, url in tree['available'])
                broken = lab_controllers.difference(available_lcs)
                if not onlybroken or broken:
                    print('%s %s %s %s Tags:%s' % (tree['distro_tree_id'],
                                                   tree['distro_name'], tree['variant'] or '',
                                                   tree['arch'], ','.join(tree['distro_tags'])))
                    if broken:
                        print("missing from labs %s" % list(broken))
        else:
            sys.stderr.write("Nothing Matches\n")
            sys.exit(1)
