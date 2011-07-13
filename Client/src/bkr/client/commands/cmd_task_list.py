# -*- coding: utf-8 -*-

"""
List tasks in Beaker's task library
===================================

.. program:: bkr task-list

Synopsis
--------

| :program:`bkr task-list` [*options*]
|       [--type=<type> ...] [--package=<package> ...] [--install_name=<name>]
|       [--xml [--params=<name>=<value> ...]]

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

.. option:: --install_name <name>

   Limit to tasks which apply to distro with install name <name>.

   Note that this must be the distro's *install name*. This is the first field 
   in the output of :program:`bkr distros-list`.

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

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand
from optparse import OptionValueError
import sys
import os.path
import xmlrpclib
from xml.dom.minidom import Document, parseString

class Task_List(BeakerCommand):
    """List tasks available for distro"""
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
            "--install_name",
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


    def run(self, *args, **kwargs):
        filter = dict()
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        filter['types'] = kwargs.pop("type", None)
        filter['packages'] = kwargs.pop("package", None)
        filter['install_name'] = kwargs.pop("install_name", None)
        filter['valid'] = True
        params = kwargs.pop("params", [])
        xml = kwargs.pop("xml")

        self.set_hub(username, password)
        doc = Document()
        xmlparams = doc.createElement('params')
        for param in params:
            try:
                (key, value) = param.split('=',1)
            except ValueError:
                print "Params must be KEY=VALUE %s is not" % param
                sys.exit(1)
            xmlparam = doc.createElement('param')
            xmlparam.setAttribute('name', '%s' % key)
            xmlparam.setAttribute('value', '%s' % value)
            xmlparams.appendChild(xmlparam)
        for task in self.hub.tasks.filter(filter):
            if xml:
                xmltask = doc.createElement('task')
                xmltask.setAttribute('name', task)
                xmltask.appendChild(xmlparams)
                print xmltask.toprettyxml()
            else:
                print task
