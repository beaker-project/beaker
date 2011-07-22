# -*- coding: utf-8 -*-

"""
Watch the progress of a Beaker job
==================================

.. program:: bkr job-watch

Synopsis
--------

:program:`bkr job-watch` [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be watched. Each state change will 
be reported to stdout. The command will exit only when everything is finished.

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

Bugs
----

In its current implementation this command polls the Beaker server periodically 
for state changes. To avoid overloading the server, only the given <taskspec> 
arguments and none of their subcomponents are watched. This limitation will 
be addressed in an upcoming release (most likely by switching to a message 
bus).

Examples
--------

Watch the progress of job 12345 and all recipes within it::

    bkr job-watch J:12345

Due to the limitation noted above, this won't actually watch any recipes within 
the job, although it should.

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client import BeakerCommand
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


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        nowait   = kwargs.pop("nowait", None)

        self.set_hub(username, password)
        if not nowait:
            TaskWatcher.watch_tasks(self.hub, args)
