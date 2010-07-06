# -*- coding: utf-8 -*-


from bkr.client import BeakerCommand
from optparse import OptionValueError
from bkr.client.task_watcher import *
from xml.dom.minidom import Document, parseString

class Job_Results(BeakerCommand):
    """Get Jobs/Recipes Results"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name
        self.parser.add_option(
            "--prettyxml",
            default=False,
            action="store_true",
            help="Pretty print the xml",
        )


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        prettyxml   = kwargs.pop("prettyxml", None)

        self.set_hub(username, password)
        for task in args:
            myxml = self.hub.taskactions.to_xml(task)
            if prettyxml:
                print parseString(myxml).toprettyxml()
            else:
                print myxml
