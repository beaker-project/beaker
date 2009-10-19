# -*- coding: utf-8 -*-


from beaker.client import BeakerCommand
from optparse import OptionValueError


class Job_Submit(BeakerCommand):
    """ Submit job to scheduler """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        if len(args) > 0:
            job = open(args[0], "r").read()

        self.set_hub(username, password)
        jobid = self.hub.jobs.upload(job)
        if jobid:
            print "Successfully submitted, job id:%s" % jobid
