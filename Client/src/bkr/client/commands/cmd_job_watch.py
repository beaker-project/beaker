# -*- coding: utf-8 -*-


from bkr.client import BeakerCommand
from bkr.client.message_bus import ClientBeakerBus
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

        self.parser.add_option(
            "--listenuntil",
            type="string",
            help="To which subtask below the current to listen for. \
                  Ignored if not using message bus. Must be lower than task watching.\
                  Undetermined behaviour when listening on multiple tasks",
        )


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        nowait   = kwargs.pop("nowait", None)
        if not args:
            self.parser.error('Please specify one or more tasks')

        self.set_hub(username, password)
        if self.conf.get('MSG_BUS') is True:
            listendepth = kwargs.get('listenuntil')
            if listendepth:
                if listendepth not in TaskWatcherBus.task_depth_order:
                    self.parser.error('Invalid value for listen')
                    return
            TaskWatcherBus.watch_tasks(listendepth, list(args))
        else:
            if not nowait:
                TaskWatcher.watch_tasks(self.hub, args)
