# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-machine-test:

bkr machine-test: Generate Beaker job to test a system
======================================================

.. program:: bkr machine-test

Synopsis
--------

:program:`bkr machine-test` :option:`--machine <bkr --machine>` <fqdn> [--inventory] [*workflow options*] [*options*]

Description
-----------

Generates a Beaker job to test the system identified by <fqdn>.

Options
-------

.. option:: --inventory

   Include the /distribution/inventory task in the generated job, in order to 
   update the system's details in Beaker.

Common workflow options are described in the :ref:`Workflow options 
<workflow-options>` section of :manpage:`bkr(1)`.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Test a particular system on RHEL5 and RHEL6, including running the inventory 
task::

    bkr machine-test --machine=system1.example.invalid --inventory \\
            --family RedHatEnterpriseLinuxServer5 \\
            --family RedHatEnterpriseLinux6

Attempt to run the inventory task on faultysystem.example.invalid even
though it is marked as Broken::

   bkr machine-test --ignore-system-status --inventory \\
            --machine=faultysystem.example.invalid

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand, BeakerWorkflow, BeakerJob, BeakerRecipeSet, BeakerRecipe
from optparse import OptionValueError
import sys
import copy
import xml.dom.minidom

class Machine_Test(BeakerWorkflow):
    """Workflow to generate job to test machines"""
    enabled = True
    doc = xml.dom.minidom.Document()

    def options(self):
        super(Machine_Test, self).options()

        self.parser.remove_option("--family")
        self.parser.remove_option("--clients")
        self.parser.remove_option("--servers")
        self.parser.remove_option("--hostrequire")
        self.parser.remove_option("--keyvalue")
        self.parser.remove_option("--systype")
        self.parser.remove_option("--random")
        self.parser.remove_option("--distro")
        # Re-add option Family with append options
        self.parser.add_option(
            "--family",
            action="append",
            default=[],
            help="Test machine with this family",
        )
        self.parser.add_option(
            "--inventory",
            action="store_true",
            default=False,
            help="Run Inventory task as well"
        )
        self.parser.usage = "%%prog %s [options] --machine=FQDN" % self.normalized_name

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)

        debug  = kwargs.get("debug", False)
        dryrun = kwargs.get("dryrun", False)
        wait = kwargs.get("wait", False)
        machine = kwargs.get("machine", None)
        families = kwargs.get("family", [])
        taskParams = kwargs.get("taskparam", [])

        # Add in Inventory if requested
        if kwargs.get("inventory"):
            kwargs['task'].append('/distribution/inventory')

        if not machine:
            self.parser.error('Use --machine to specify machine to be tested')

        if not kwargs.get("whiteboard"):
            kwargs["whiteboard"] = "Test %s" % machine

        # If family is specified on command line just do it.
        if kwargs['family']:
            if not kwargs['arches']:
                self.parser.error("If family is specified you must specify arches as well")
            families = dict((family, [arch for arch in kwargs['arches']]) for family in kwargs['family'])
        else:
            families = self.getSystemOsMajorArches(*args, **kwargs)

        # Exit early
        if not families:
            print >>sys.stderr, 'Could not find an appropriate distro to provision system with.'
            sys.exit(1)

        # Create Job
        job = BeakerJob(*args, **kwargs)

        for family, arches in families.items():
            kwargs['family'] = family
            # Start with install task
            requestedTasks = [dict(name='/distribution/install', arches=[])]

            # get all tasks requested
            requestedTasks.extend(self.getTasks(*args, **kwargs))
            # If arch is specified on command line limit to just those. (if they match)
            if kwargs['arches']:
                arches = set(kwargs['arches']).intersection(set(arches))
            for arch in arches:
                recipeTemplate =  BeakerRecipe()
                # Add Distro Requirements
                temp = dict(kwargs)
                temp['family'] = family
                recipeTemplate.addBaseRequires(*args, **temp)
                arch_node = self.doc.createElement('distro_arch')
                arch_node.setAttribute('op', '=')
                arch_node.setAttribute('value', arch)
                recipeSet = BeakerRecipeSet(**kwargs)
                recipeSet.addRecipe(self.processTemplate(recipeTemplate,
                                                         requestedTasks,
                                                         taskParams=taskParams,
                                                         distroRequires=arch_node, **temp))
                job.addRecipeSet(recipeSet)

        # jobxml
        jobxml = job.toxml(**kwargs)

        if debug:
            print jobxml

        submitted_jobs = []
        failed = False

        if not dryrun:
            try:
                submitted_jobs.append(self.hub.jobs.upload(jobxml))
            except Exception, ex:
                failed = True
                print >>sys.stderr, ex
        if not dryrun:
            print "Submitted: %s" % submitted_jobs
            if wait:
                watch_tasks(self.hub, submitted_jobs)
            if failed:
                sys.exit(1)
