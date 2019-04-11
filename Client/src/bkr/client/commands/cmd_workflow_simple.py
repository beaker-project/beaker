# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-workflow-simple:

bkr workflow-simple: Simple workflow to generate Beaker jobs
============================================================

.. program:: bkr workflow-simple

Synopsis
--------

:program:`bkr workflow-simple` [*workflow options*] [*options*]

Description
-----------

Generates a Beaker job using the (not-so-simple) options available for all 
workflows.

Options
-------

Common workflow options are described in the :ref:`Workflow options 
<workflow-options>` section of :manpage:`bkr(1)`.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Schedule a job using CentOS 7 Server, containing the hypothetical
``/mypackage/mytest`` task on a randomly selected x86_64 machine::

    bkr workflow-simple --arch x86_64 --random \\
            --family CentOS7 --variant Server \\
            --task /mypackage/mytest

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import sys
import xml.dom.minidom

from six.moves.xmlrpc_client import Fault

from bkr.client import BeakerJob
from bkr.client import BeakerRecipe
from bkr.client import BeakerRecipeSet
from bkr.client import BeakerWorkflow
from bkr.client.task_watcher import *


class Workflow_Simple(BeakerWorkflow):
    """
    Simple workflow to generate job to scheduler
    """
    enabled = True
    doc = xml.dom.minidom.Document()

    def options(self):
        super(Workflow_Simple, self).options()
        self.parser.usage = "%%prog %s [options]" % self.normalized_name

    def run(self, *args, **kwargs):

        if not kwargs.get("package", []) and not kwargs.get("task", []) \
                and not kwargs.get("taskfile", []) and not kwargs.get("type", []):
            self.parser.error('No tasks specified to be run\nHint: '
                              'Use --task, --package, --taskfile or --task-type to select tasks\n')

        self.set_hub(**kwargs)

        debug = kwargs.get("debug", False)
        dryrun = kwargs.get("dryrun", False)
        wait = kwargs.get("wait", False)
        family = kwargs.get("family", None)
        distro = kwargs.get("distro", None)
        arches = kwargs.get("arches", [])
        taskParams = kwargs.get("taskparam", [])

        if not family and not distro:
            sys.stderr.write("No Family or Distro specified\n")
            sys.exit(1)

        if not arches:
            # Get default arches that apply for this distro/family
            arches = self.get_arches(*args, **kwargs)

        # get all tasks requested
        try:
            requested_tasks = self.get_tasks(*args, **kwargs)
        except Fault:
            requested_tasks = None

        if not requested_tasks:
            sys.stderr.write("No tasks match the specified option(s)\n")
            sys.exit(1)

        # Create Job
        job = BeakerJob(*args, **kwargs)

        # Create Base Recipe
        recipe_template = BeakerRecipe()

        # Add Distro Requirements
        recipe_template.add_base_requires(*args, **kwargs)

        # Add Host Requirements
        for arch in arches:
            arch_node = self.doc.createElement('distro_arch')
            arch_node.setAttribute('op', '=')
            arch_node.setAttribute('value', arch)
            recipe_set = BeakerRecipeSet(**kwargs)
            if self.multi_host:
                for i in range(self.n_servers):
                    recipe_set.add_recipe(self.process_template(recipe_template,
                                                                requested_tasks,
                                                                taskParams=taskParams,
                                                                distroRequires=arch_node,
                                                                role='SERVERS',
                                                                arch=arch,
                                                                **kwargs))
                for i in range(self.n_clients):
                    recipe_set.add_recipe(self.process_template(recipe_template,
                                                                requested_tasks,
                                                                taskParams=taskParams,
                                                                distroRequires=arch_node,
                                                                role='CLIENTS',
                                                                arch=arch,
                                                                **kwargs))
            else:
                recipe_set.add_recipe(self.process_template(recipe_template,
                                                            requested_tasks,
                                                            taskParams=taskParams,
                                                            distroRequires=arch_node,
                                                            arch=arch,
                                                            **kwargs))
            job.add_recipe_set(recipe_set)

        # jobxml
        jobxml = job.toxml(**kwargs)

        if debug:
            print(jobxml)

        submitted_jobs = []
        is_failed = False
        if not dryrun:
            try:
                submitted_jobs.append(self.hub.jobs.upload(jobxml))
                print("Submitted: %s" % submitted_jobs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as ex:
                is_failed = True
                sys.stderr.write('Exception: %s\n' % ex)
            if wait:
                is_failed |= watch_tasks(self.hub, submitted_jobs)
        sys.exit(is_failed)
