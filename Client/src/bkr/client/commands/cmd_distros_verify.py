# -*- coding: utf-8 -*-

"""
Check Beaker distros for problems
=================================

.. program:: bkr distros-verify

Synopsis
--------

| :program:`bkr distros-verify` [*options*]
|       [--tag=<tag>] [--name=<name>] [--treepath=<url>] [--family=<family>] [--arch=<arch>]
|       [--broken] [--limit=<number>]

Description
-----------

Prints to stdout a list of matching distros in Beaker, along with a list of 
labs (if any) which do not have the distro.

Options
-------

.. option:: --tag <tag>

   Limit to distros which have been tagged in Beaker with <tag>.

.. option:: --name <name>

   Limit to distros with the given name. <name> is interpreted as a SQL LIKE 
   pattern (the % character matches any substring).

.. option:: --treepath <url>

   Limit to distros with the given tree path. <url> is interpreted as a SQL LIKE 
   pattern (the % character matches any substring).

.. option:: --family <family>

   Limit to distros of the given family (major version), for example 
   ``RedHatEnterpriseLinuxServer5``.

.. option:: --arch <arch>

   Limit to distros for the given arch.

.. option:: --broken

   Limit to distros which are not present in every lab.

.. option:: --limit <number>

   Return at most <number> distros.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.
If no distros match the given criteria this is considered to be an error, and 
the exit status will be 1.

See also
--------

:manpage:`bkr-distros-list(1)`, :manpage:`bkr(1)`
"""


import sys
from bkr.client import BeakerCommand


class Distros_Verify(BeakerCommand):
    """verify distros"""
    enabled = True


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
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        onlybroken = kwargs.pop("broken", False)
        filter = dict( limit    = kwargs.pop("limit", None),
                       name     = kwargs.pop("name", None),
                       treepath = kwargs.pop("treepath", None),
                       family   = kwargs.pop("family", None),
                       arch     = kwargs.pop("arch", None),
                       tags     = kwargs.pop("tag", []),
                     )

        self.set_hub(username, password)
        lab_controllers = set(self.hub.lab_controllers())
        distros = self.hub.distros.filter(filter)
        if distros:
            for distro in distros:
                broken = lab_controllers.difference(set(distro[8]))
                if not onlybroken or broken:
                    print "%s Tags:%s" % (distro[0], distro[7])
                    if broken:
                        print "missing from labs %s" % list(broken)
        else:
            sys.stderr.write("Nothing Matches\n")
            sys.exit(1)
