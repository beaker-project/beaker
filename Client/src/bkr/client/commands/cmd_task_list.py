# -*- coding: utf-8 -*-


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand
from optparse import OptionValueError
import sys
import os.path
import xmlrpclib
from xml.dom.minidom import Document, parseString

class Task_List(BeakerCommand):
    """List tasks available for distro"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <install_name>..." % self.normalized_name
        self.parser.add_option(
            "--type",
            action="append",
            help="Only return tasks of these types (Tier1, KernelTier1, Regression)",
        )
        self.parser.add_option(
            "--package",
            action="append",
            help="Only return tasks that apply to these packages (kernel, apache, postgresql)",
        )
        self.parser.add_option(
            "--params",
            action="append",
            help="if xml is enabled, add these params as args to each task",
        )
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
        filter['types'] = kwargs.pop("type", None)
        filter['packages'] = kwargs.pop("package", None)
        params = kwargs.pop("params", [])
        xml = kwargs.pop("xml")

        install_name = args[0]

        self.set_hub(username, password)
        doc = Document()
        for param in params:
            try:
                (key, value) = param.split('=',1)
            except ValueError:
                print "Params must be KEY=VALUE %s is not" % param
                sys.exit(1)
            xmlparam = doc.createElement('param')
            xmlparam.setAttribute('name', '%s' % key)
            xmlparam.setAttribute('value', '%s' % value)
            xmlparams.appendChild(xmlparam)
        for task in self.hub.tasks.filter(install_name, filter):
            if xml:
                xmltask = doc.createElement('task')
                xmltask.setAttribute('name', task)
                xmltask.appendChild(xmlparams)
                print xmltask.toprettyxml()
            else:
                print task
