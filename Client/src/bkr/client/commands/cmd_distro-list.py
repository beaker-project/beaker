# -*- coding: utf-8 -*-


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
