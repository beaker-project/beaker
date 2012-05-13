
"""
Modify Beaker jobs
================

.. program:: bkr job-modify

Synopsis
--------

| :program:`bkr job-modify` [*options*] [--response=<response>]

Description
-----------

Allows ack/nak of a job.

.. _job-modify-options:

Options
-------

.. option:: --response <response>

   Sets the response type of the job. Can be either 'ack' or 'nak'

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Set a recipe set to 'ack':

    bkr job-modify RS:1 --response ack

Set multiple jobs to be 'nak':

    bkr job-modify J:1 J:2 --response nak

See also
--------

:manpage:`bkr(1)`
"""
from bkr.client import BeakerCommand
from xmlrpclib import Fault

class Job_Modify(BeakerCommand):

    enabled = True
    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option(
            "-r",
            "--response",
            help = "Set a job or recipesets response. Valid values are 'ack' or 'nak'",
         )

    def run(self, *args, **kw):
        username = kw.pop("username", None)
        password = kw.pop("password", None)
        response = kw.pop('response', None)
        valid_jobs = []
        self.set_hub(username, password)
        types = self.hub.get_job_types()
        valid_codes = []
        for code, type in types.iteritems():
            if type == 'Job':
                valid_codes.append(code)
            if type == 'RecipeSet':
                valid_codes.append(code)

        for job in args:
            type,number = job.split(':')
            try:
                valid_codes.index(type)
            except ValueError:
                self.parser.error('Arguments must be in a valid job format')
            valid_jobs.append(job)
        modded = []
        if response:
            try:
                for job in valid_jobs:
                    self.hub.jobs.set_response(job, response)
                    modded.append(job)
            except Fault, e:
                print str(e)
        if modded:
            print 'Successfully modified jobs %s' % ' '.join(modded)
        else:
            print 'No jobs modified'
