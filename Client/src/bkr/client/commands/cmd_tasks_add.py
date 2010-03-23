# -*- coding: utf-8 -*-


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand
from optparse import OptionValueError
import sys
import os.path
import xmlrpclib

class Tasks_Add(BeakerCommand):
    """Add/Update task to scheduler"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskrpm>..." % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        tasks = args

        self.set_hub(username, password)
        for task in tasks:
            task_name = os.path.basename(task)
            task_binary = xmlrpclib.Binary(open(task, "r").read())
            print task_name
            try:
                print self.hub.tasks.upload(task_name, task_binary)
            except Exception, ex:
                print ex
