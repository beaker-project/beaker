# -*- coding: utf-8 -*-

from bkr.client import BeakerCommand
from optparse import OptionValueError


class Watchdog_Extend(BeakerCommand):
    """Extend Task's Watchdog"""
    enabled = True

    def options(self):
        self.parser.add_option(
            "--by",
            default=7200, type="int",
            help="Time in seconds to extend the watchdog by.",
        )

        self.parser.usage = "%%prog %s [options] <task_id>..." % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        extend_by = kwargs.pop("by", None)

        self.set_hub(username, password)
        for task_id in args:
            print self.hub.recipes.tasks.extend(task_id, extend_by)

