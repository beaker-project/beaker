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

Prints to stdout the details of all matching Beaker distros. The output 
contains a header line, followed by one line per distro.

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

List details of all RHEL5.6 Server nightly trees from a particular date::

    bkr distros-list --name "RHEL5.6-Server-20101110%"

See also
--------

:manpage:`bkr(1)`
"""


import sys
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
        filter = dict( limit    = kwargs.pop("limit", None),
                       name     = kwargs.pop("name", None),
                       treepath = kwargs.pop("treepath", None),
                       family   = kwargs.pop("family", None),
                       arch     = kwargs.pop("arch", None),
                       tags     = kwargs.pop("tag", []),
                     )

        self.set_hub(username, password)
        distros = self.hub.distros.filter(filter)
        if distros:
            print "InstallName,Name,Arch,OSVersion,Variant,Method,Virt,[Tags,],{LabController:Path,}"
            for distro in distros:
                print ','.join([str(d) for d in distro])
        else:
            sys.stderr.write("Nothing Matches\n")
            sys.exit(1)
