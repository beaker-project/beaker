# -*- coding: utf-8 -*-

"""
bkr job-clone: Clone existing Beaker jobs
=========================================

.. program:: bkr job-clone

Synopsis
--------

| :program:`bkr job-clone` [*options*]
|       [--wait] [--dryrun] [--xml] [--prettyxml] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be cloned. A new job will be 
created for each argument. The cloned job ids will be printed to stdout.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Only jobs and recipe sets may be cloned.

Options
-------

.. option:: --wait

   When this option is given, the command will not terminate until the clone 
   job has finished running.

.. option:: --xml

   Print the job XML before submitting it.

.. option:: --prettyxml

   Print the job XML in a easily readable format before submitting it.

.. option:: --dryrun

   Run through the job-clone process without actually submitting the cloned job



Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.
A failure in cloning *any* of the arguments is considered to be an error, and 
the exit status will be 1.

Examples
--------

Clone job 1234 and wait for it to finish::

    bkr job-clone --wait J:1234

See also
--------

:manpage:`bkr(1)`
"""

import sys
from bkr.client import BeakerCommand
from optparse import OptionValueError
from bkr.client.task_watcher import *
from xml.dom.minidom import parseString

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
        self.parser.add_option(
            "--dryrun",
            default=False,
            action="store_true",
            help="Test the likely output of job-clone without cloning anything",
        )
        self.parser.add_option(
            "--xml",
            default=False,
            action="store_true",
            help="print the jobxml that it would submit",
        )
        self.parser.add_option(
            "--prettyxml",
            action="store_true",
            default=False,
            help="print the jobxml that it would submit, in pretty format",
        )

    def run(self, *args, **kwargs):
        self.check_taskspec_args(args, permitted_types=['J', 'RS'])

        wait = kwargs.pop("wait", None)
        xml = kwargs.pop("xml", None)
        pretty = kwargs.pop("prettyxml", None)
        dryrun = kwargs.pop("dryrun", None)

        submitted_jobs = []
        failed = False
        clone = True
        self.set_hub(**kwargs)
        for task in args:
            try:
                task_type, task_id = task.split(":")
                if task_type.upper() == 'RS':
                    from_job = False
                else:
                    from_job = True
                jobxml = self.hub.taskactions.to_xml(task,clone,from_job)
                if pretty:
                    print parseString(jobxml).toprettyxml()
                elif xml:
                    print parseString(jobxml).toxml()
                if not dryrun:
                    submitted_jobs.append(self.hub.jobs.upload(jobxml))
            except Exception, ex:
                failed = True
                print ex
        if not dryrun:
            print "Submitted: %s" % submitted_jobs
            if wait:
                watch_tasks(self.hub, submitted_jobs)
        if failed:
            sys.exit(1)
