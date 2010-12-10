# -*- coding: utf-8 -*-

import sys
from bkr.client import BeakerCommand
from optparse import OptionValueError
from bkr.client.task_watcher import *

class Job_Clone(BeakerCommand):
    """Clone Jobs/RecipeSets"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name
        self.parser.add_option(
            "--wait",
            default=False,
            action="store_true",
            help="wait on job completion",
        )


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        wait = kwargs.pop("wait", None)

        submitted_jobs = []
        failed = False
        clone = True
        self.set_hub(username, password)
        for task in args:
            try:
                task_type, task_id = task.split(":")
                if task_type.upper() == 'RS':
                    from_job = False
                else:
                    from_job = True
                submitted_jobs.append(self.hub.jobs.upload(self.hub.taskactions.to_xml(task,clone,from_job)))
            except Exception, ex:
                failed = True
                print ex
        print "Submitted: %s" % submitted_jobs
        if wait:
            TaskWatcher.watch_tasks(self.hub, submitted_jobs)
        if failed:
            sys.exit(1)
