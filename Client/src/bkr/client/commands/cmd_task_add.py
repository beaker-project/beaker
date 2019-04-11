# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-task-add:

bkr task-add: Upload tasks to Beaker's task library
===================================================

.. program:: bkr task-add

Synopsis
--------

:program:`bkr task-add` [*options*] <taskrpm>...

Description
-----------

Uploads one or more task RPM packages to Beaker's task library. These tasks 
will be available for jobs queued with the Beaker scheduler.

If updating an existing task in Beaker, the RPM version of the new package must 
be greater than the version currently in Beaker.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Upload a new version of the /distribution/beaker/dogfood task::

    bkr task-add beaker-distribution-beaker-dogfood-2.0-1.rpm

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import os.path
import sys

from six.moves import xmlrpc_client

from bkr.client import BeakerCommand


class Task_Add(BeakerCommand):
    """
    Add/Update task to scheduler
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskrpm>..." % self.normalized_name

    def run(self, *args, **kwargs):
        tasks = args

        self.set_hub(**kwargs)
        failed = False
        for task in tasks:
            task_name = os.path.basename(task)
            task_binary = xmlrpc_client.Binary(open(task, "rb").read())
            print(task_name)
            try:
                print(self.hub.tasks.upload(task_name, task_binary))
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as ex:
                failed = True
                sys.stderr.write('Exception: %s\n' % ex)

        if failed:
            sys.exit(1)
