# -*- coding: utf-8 -*-

"""
List Beaker distros
===================

.. program:: bkr distros-list

Synopsis
--------

| :program:`bkr distros-list` [*options*]
|       [--tag=<tag>] [--name=<name>] [--treepath=<url>] [--family=<family>] [--arch=<arch>]
|       [--limit=<number>]

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

.. option:: --limit <number>

   Return at most <number> distros.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.
If no distros match the given criteria this is considered to be an error, and 
the exit status will be 1.

Examples
--------

List details of all RHEL6 distros with the RELEASED tag::

    bkr distros-list --family RedHatEnterpriseLinux6 --tag RELEASED

History
-------

Prior to version 0.9, this command also accepted :option:`--treepath`, 
:option:`--labcontroller`, and :option:`--arch` filter options. Use 
:program:`bkr distro-trees-list` instead.

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-distro-trees-list(1)`
"""


import sys
try:
    import json
except ImportError:
    import simplejson as json
from bkr.client import BeakerCommand


class Distros_List(BeakerCommand):
    """list distros"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

        self.parser.add_option(
            "--limit",
            default=10,
            type=int,
            help="Limit results to this many (default 10)",
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


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        filter = dict( limit    = kwargs.pop("limit", None),
                       name     = kwargs.pop("name", None),
                       family   = kwargs.pop("family", None),
                       tags     = kwargs.pop("tag", []),
                     )

        self.set_hub(username, password)
        distros = self.hub.distros.filter(filter)
        if distros:
            print json.dumps(distros, indent=4)
        else:
            sys.stderr.write("Nothing Matches\n")
            sys.exit(1)
