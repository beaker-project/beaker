# -*- coding: utf-8 -*-

from bkr.client import BeakerCommand
from optparse import OptionValueError


class Watchdog_Show(BeakerCommand):
    """Display Task's Watchdog"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <task_id>..." % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        self.set_hub(username, password)
        for task_id in args:
            print "%s: %s" % (task_id, self.hub.recipes.tasks.watchdog(task_id))

