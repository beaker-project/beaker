# -*- coding: utf-8 -*-


from bkr.client import BeakerCommand


class Distros_Tag(BeakerCommand):
    """tag distros"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s [options] <tag>" % self.normalized_name

        self.parser.add_option(
            "--name",
            default=None,
            help="tag by name, use % for wildcard",
        )
        self.parser.add_option(
            "--arch",
            default=None,
            help="tag by arch",
        )


    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a tag")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        name = kwargs.pop("name", None)
        arch = kwargs.pop("arch", None)
        tag = args[0]

        self.set_hub(username, password)
        print "Tagged the following distros with tag: %s" % tag
        print "------------------------------------------------------"
        for distro in self.hub.distros.tag(name, arch, tag):
            print distro
