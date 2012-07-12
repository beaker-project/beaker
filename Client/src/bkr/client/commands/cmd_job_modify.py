# -*- coding: utf-8 -*-

"""
bkr job-modify: Modify Beaker jobs
==================================

.. program:: bkr job-modify

Synopsis
--------

| :program:`bkr job-modify` [*options*] [--response=<response>] <taskspec>...

Description
-----------

Allows ack/nak of a job.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

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
from sys import exit

class Job_Modify(BeakerCommand):
    """Modify certain job properties """

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

        self.check_taskspec_args(args, permitted_types=['J', 'RS'])
        modded = []
        error = False
        if response:
            try:
                for job in args:
                    self.hub.jobs.set_response(job, response)
                    modded.append(job)
            except Fault, e:
                print str(e)
                error = True
        if modded:
            print 'Successfully modified jobs %s' % ' '.join(modded)
        else:
            print 'No jobs modified'

        if error:
            exit(1)
        else:
            exit(0)
