# -*- coding: utf-8 -*-

"""
bkr job-watch: Watch the progress of a Beaker job
=================================================

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

import sys
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
            "-v",
            action='count',
            dest='verbosity',
            help="the number of verbose indicates to how many subtasks down it will listen \
                  Ignored if not using message bus. Must be lower than task watching.\
                  Undetermined behaviour when listening on multiple tasks",
        )


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        if not args:
            self.parser.error('Please specify one or more tasks')

        if self.conf.get('QPID_BUS') is True:
            listendepth = kwargs.get('verbosity') or 0
            task_args = list(args)
            task_type = [task.split(':')[0] for task in task_args]
            failed = [t for t in task_type if t not in TaskBus.task_depth_order]
            if len(failed) > 0:
                self.parser.error('%s are not valid task types' % ','.join(failed))
            sys.exit(watch_bus_tasks(int(listendepth), task_args))
        else:
            self.set_hub(username, password)
            sys.exit(watch_tasks(self.hub, args))
