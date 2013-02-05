# -*- coding: utf-8 -*-

"""
.. _bkr-job-logs:

bkr job-logs: Print URLs of Beaker recipe log files
===================================================

.. program:: bkr job-logs

Synopsis
--------

:program:`bkr job-logs` [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be exported. A list of the 
log files for each argument will be printed to stdout.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Display logs for job 12345::

    bkr job-logs J:12345

See also
--------

:manpage:`bkr(1)`
"""

import sys
from bkr.client import BeakerCommand
from optparse import OptionValueError
from bkr.client.task_watcher import *
import libxml2

class Job_Logs(BeakerCommand):
    """Print URLs of recipe log files"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name


    def run(self, *args, **kwargs):
        self.check_taskspec_args(args)

        self.set_hub(**kwargs)
        for task in args:
            logfiles = self.hub.taskactions.files(task)
            for log in logfiles:
                print log['url']
