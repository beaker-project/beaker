# -*- coding: utf-8 -*-

"""
Clone existing Beaker jobs
==========================

.. program:: bkr job-clone

Synopsis
--------

:program:`bkr job-clone` [--wait] [*options*] <taskspec>...

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

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

1 if there was an error cloning any of the arguments, otherwise zero.

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
