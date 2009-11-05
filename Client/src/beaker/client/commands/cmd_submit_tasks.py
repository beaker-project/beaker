# -*- coding: utf-8 -*-


from beaker.client.task_watcher import *
from beaker.client import BeakerCommand
from optparse import OptionValueError
import sys

class Submit_Tasks(BeakerCommand):
    """ Submit job(s) to scheduler """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        jobs = args
        if len(args) > 0:
            job = open(args[0], "r").read()

        self.set_hub(username, password)
        submitted_jobs = []
        failed = False
        for job in jobs:
            try:
                submitted_jobs.append(self.hub.jobs.upload(open(job, "r").read()))
            except Exception, ex:
                failed = True
                print ex
        TaskWatcher.watch_tasks(self.hub, submitted_jobs)
        for submitted_job in submitted_jobs:
            print self.hub.taskactions.to_xml(submitted_job)
        if failed:
            sys.exit(1)
