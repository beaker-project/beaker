# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-task-delete:

bkr task-delete: Delete tasks to Beaker's task library
======================================================

.. program:: bkr task-delete

Synopsis
--------

:program:`bkr task-delete` [*options*] <task_name>...

Description
-----------

Deletes one or more task RPM packages to Beaker's task library. These tasks
will be no longer available for jobs queued with the Beaker scheduler.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Delete a particular task::

    bkr task-delete /distribution/beaker/dogfood

Notes
-----

This command is only available to Beaker administrators.

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import json
import sys

from six.moves import xmlrpc_client

from bkr.client import BeakerCommand


class Task_Delete(BeakerCommand):
    """
    Delete task from task library
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <task_name>..." % self.normalized_name

    def run(self, *args, **kwargs):
        tasks = args

        self.set_hub(**kwargs)
        failed = False
        for task in tasks:
            try:
                task_id = self.hub.tasks.to_dict(task)['id']
                output = json.loads(self.hub.tasks.disable_from_ui(task_id))
                print('{}: {}'.format('success' if output['success'] else 'failed', task))
                failed = not output['success']
            except (KeyboardInterrupt, SystemExit):
                raise
            except xmlrpc_client.Fault as ex:
                failed = True
                sys.stderr.write(ex.faultString + '\n')
            except Exception as ex:
                failed = True
                sys.stderr.write('Exception: %s\n' % ex)
        exit(failed)
