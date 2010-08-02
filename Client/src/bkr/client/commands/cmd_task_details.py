# -*- coding: utf-8 -*-


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand
from optparse import OptionValueError
import sys
import os.path
import xmlrpclib
from xml.dom.minidom import Document, parseString

class Task_Details(BeakerCommand):
    """Show details about Task"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option(
            "--xml",
            default=False,
            action="store_true",
            help="print as xml",
        )


    def run(self, *args, **kwargs):
        filter = dict()
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        xml = kwargs.pop("xml")

        self.set_hub(username, password)
        for task in args:
            print "%s %s" % (task, self.hub.tasks.to_dict(task))
