# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr task-list: List tasks in Beaker's task library
==================================================

.. program:: bkr task-list

Synopsis
--------

| :program:`bkr task-list` [*options*]
|       [:option:`--type` <type> ...] [:option:`--package` <package> ...] [:option:`--distro` <name>]
|       [--xml [:option:`--params` <name>=<value> ...]]

Description
-----------

Prints to stdout a list of matching tasks from the Beaker task library.

Options
-------

.. option:: --type <type>

   Limit to tasks of type <type>. This corresponds to the ``Type:`` field in 
   the task metadata and on the task page in Beaker's web UI.

   This option may be specified more than once, in which case an "or" operator 
   is applied. That is, a task will be listed if it matches any of the given 
   types.

.. option:: --package <package>

   Limit to tasks which apply to <package>. This corresponds to the ``RunFor:`` 
   field in the task metadata, and the ``Run For`` field on the task page in 
   Beaker's web UI.

   This option may be specified more than once, in which case an "or" operator 
   is applied. That is, a task will be listed if it applies to any of the 
   given packages.

.. option:: --destructive

   Limit to tasks which are destructive (Note: excludes both non-destructive
   and unmarked tasks).

.. option:: --non-destructive

   Limit to tasks which are non-destructive (Note: excludes both destructive
   and unmarked tasks).

.. option:: --distro <name>

   Limit to tasks which apply to distro <name>.

.. option:: --xml

   Output task listing as XML, with one ``<task/>`` element per task. This 
   output is suitable for inclusion inside the ``<tasks/>`` element of a Beaker 
   XML job.

.. option:: --params <name>=<value>

   When :option:`--xml` is passed, this will cause a ``<param/>`` element to be 
   added inside each ``<task/>`` element.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List all regression tests which apply to the ``apache`` or ``tomcat6`` 
packages::

    bkr task-list --type=Regression --package=apache --package=tomcat6

History
-------

Prior to version 0.9, this command accepted --install_name instead of
:option:`--distro`.

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import sys
from xml.dom.minidom import Document

from bkr.client import BeakerCommand


class Task_List(BeakerCommand):
    """
    List tasks in Beaker's task library
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option(
            "--type",
            action="append",
            help="Only return tasks of these types (Tier1, KernelTier1, Regression)",
        )
        self.parser.add_option(
            "--package",
            action="append",
            help="Only return tasks that apply to these packages (kernel, apache, postgresql)",
        )
        self.parser.add_option(
            "--distro",
            default="",
            help="Only return tasks that apply to this distro",
        )
        self.parser.add_option(
            "--params",
            action="append",
            default=[],
            help="if xml is enabled, add these params as args to each task",
        )
        self.parser.add_option(
            "--xml",
            default=False,
            action="store_true",
            help="print as xml",
        )
        self.parser.add_option(
            "--destructive",
            action="store_true",
            help=("Only include destructive tasks (Note: excludes both "
                  "non-destructive and unmarked tasks)"),
        )
        self.parser.add_option(
            "--non-destructive",
            action="store_true",
            help=("Only include non-destructive tasks (Note: excludes both "
                  "destructive and unmarked tasks)"),
        )

    def run(self, *args, **kwargs):
        filter = dict()
        filter['types'] = kwargs.pop("type", None)
        filter['packages'] = kwargs.pop("package", None)
        filter['distro_name'] = kwargs.pop("distro", None)
        filter['valid'] = True

        # Make sure they didn't specify both destructive and non_destructive.
        if not kwargs.get("destructive") or not kwargs.get("non_destructive"):
            if kwargs.get("destructive", None):
                filter['destructive'] = 1
            if kwargs.get("non_destructive", None):
                filter['destructive'] = 0
        params = kwargs.pop("params", [])
        xml = kwargs.pop("xml")

        self.set_hub(**kwargs)
        doc = Document()
        xmlparams = doc.createElement('params')
        for param in params:
            try:
                (key, value) = param.split('=', 1)
            except ValueError:
                print("Params must be KEY=VALUE %s is not" % param)
                sys.exit(1)
            xmlparam = doc.createElement('param')
            xmlparam.setAttribute('name', '%s' % key)
            xmlparam.setAttribute('value', '%s' % value)
            xmlparams.appendChild(xmlparam)
        for task_dict in self.hub.tasks.filter(filter):
            if xml:
                xmltask = doc.createElement('task')
                xmltask.setAttribute('name', task_dict['name'])
                xmltask.appendChild(xmlparams)
                print(xmltask.toprettyxml())
            else:
                print(task_dict['name'])
