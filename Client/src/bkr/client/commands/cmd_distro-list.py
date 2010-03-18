# -*- coding: utf-8 -*-


import sys
from bkr.client import BeakerCommand


class Distros_List(BeakerCommand):
    """list distros"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

        self.parser.add_option(
            "--details",
            default=False,
            action="store_true",
            help="show details",
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
        name = kwargs.pop("name", None)
        treepath = kwargs.pop("treepath", None)
        family = kwargs.pop("family", None)
        arch = kwargs.pop("arch", None)
        tags = kwargs.pop("tag", [])

        self.set_hub(username, password)
        distros = self.hub.distros.list(name, family, arch, tags, treepath)
        if distros:
            if kwargs.pop("details"):
                print "Name,Arch,OSVersion,Variant,Method,Virt"
                for distro in distros:
                    print ','.join([str(d) for d in distro])
            else:
                print distros[0][0]
        else:
            sys.stderr.write("Nothing Matches\n")
            sys.exit(1)
