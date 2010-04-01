# -*- coding: utf-8 -*-


from bkr.client import BeakerCommand
from optparse import OptionValueError
from bkr.client.task_watcher import *

class Job_Watch(BeakerCommand):
    """Watch Jobs/Recipes"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name
        self.parser.add_option(
            "--nowait",
            default=False,
            action="store_true",
            help="Don't wait on job completion",
        )


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        nowait   = kwargs.pop("nowait", None)

        self.set_hub(username, password)
        if not nowait:
            TaskWatcher.watch_tasks(self.hub, args)
        for task in args:
            print self.hub.taskactions.to_xml(task)
