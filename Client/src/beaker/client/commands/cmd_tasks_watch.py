# -*- coding: utf-8 -*-


from beaker.client import BeakerCommand
from optparse import OptionValueError
from beaker.client.task_watcher import *

class Tasks_Watch(BeakerCommand):
    """Watch Tasks"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        self.set_hub(username, password)
        TaskWatcher.watch_tasks(self.hub, args)
        for task in args:
            print self.hub.taskactions.to_xml(task)
