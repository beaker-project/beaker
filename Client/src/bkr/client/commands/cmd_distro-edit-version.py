# -*- coding: utf-8 -*-


from beaker.client import BeakerCommand


class Distros_Edit_Version(BeakerCommand):
    """Edit distros version"""
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

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        name = kwargs.pop("name", None)
        version = args[0]

        self.set_hub(username, password)
        print "Updated the following distros with Version: %s" % version
        print "------------------------------------------------------"
        for distro in self.hub.distros.edit_version(name, version):
            print distro
