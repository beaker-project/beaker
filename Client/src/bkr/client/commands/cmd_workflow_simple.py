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

Schedule a job on RHEL6 Server containing all tests for the ``apache`` and 
``tomcat6`` packages on a random x86_64 machine::

    bkr workflow-simple --arch x86_64 --random \\
            --family RedHatEnterpriseLinux6 --variant Server \\
            --package apache --package tomcat6

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand, BeakerWorkflow, BeakerJob, BeakerRecipeSet, BeakerRecipe
from optparse import OptionValueError
import sys
import xml.dom.minidom

class Workflow_Simple(BeakerWorkflow):
    """Simple workflow to generate job to scheduler"""
    enabled = True
    doc = xml.dom.minidom.Document()

    def options(self):
        super(Workflow_Simple, self).options()
        self.parser.usage = "%%prog %s [options]" % self.normalized_name

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)

        # get all tasks requested
        requestedTasks = self.getTasks(*args, **kwargs)

        debug  = kwargs.get("debug", False)
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
            arches = self.getArches(*args, **kwargs)

        if not requestedTasks:
            sys.stderr.write("You must specify a package, type or task to run\n")
            sys.exit(1)

        # Create Job
        job = BeakerJob(*args, **kwargs)

        # Create Base Recipe
        recipeTemplate = BeakerRecipe()

        # Add Distro Requirements
        recipeTemplate.addBaseRequires(*args, **kwargs)

        # Add Host Requirements


        for arch in arches:
            arch_node = self.doc.createElement('distro_arch')
            arch_node.setAttribute('op', '=')
            arch_node.setAttribute('value', arch)
            recipeSet = BeakerRecipeSet(**kwargs)
            if self.multi_host:
                for i in range(self.n_servers):
                    recipeSet.addRecipe(self.processTemplate(recipeTemplate, 
                                                             requestedTasks,
                                                             taskParams=taskParams,
                                                             distroRequires=arch_node, 
                                                             role='SERVERS',
                                                             arch=arch,
                                                             **kwargs))
                for i in range(self.n_clients):
                    recipeSet.addRecipe(self.processTemplate(recipeTemplate, 
                                                             requestedTasks,
                                                             taskParams=taskParams,
                                                             distroRequires=arch_node, 
                                                             role='CLIENTS',
                                                             arch=arch,
                                                             **kwargs))
            else:
                recipeSet.addRecipe(self.processTemplate(recipeTemplate,
                                                         requestedTasks,
                                                         taskParams=taskParams,
                                                         distroRequires=arch_node,
                                                         arch=arch,
                                                         **kwargs))
            job.addRecipeSet(recipeSet)

        # jobxml
        jobxml = job.toxml(**kwargs)

        if debug:
            print jobxml

        submitted_jobs = []
        is_failed = False

        if not dryrun:
            try:
                submitted_jobs.append(self.hub.jobs.upload(jobxml))
                print "Submitted: %s" % submitted_jobs
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, ex:
                is_failed = True
                sys.stderr.write('Exception: %s\n' % ex)
            if wait:
                is_failed |= watch_tasks(self.hub, submitted_jobs)
        sys.exit(is_failed)
