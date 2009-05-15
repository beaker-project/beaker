# -*- coding: utf-8 -*-


from beaker.client import BeakerCommand


class List_LabControllers(BeakerCommand):
    """list labcontrollers"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        self.set_hub(username, password)
        print self.hub.lab_controllers()
