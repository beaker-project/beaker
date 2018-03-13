# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-workflow-reserve:

bkr workflow-reserve: Workflow to reserve a system
==================================================

.. program:: bkr workflow-reserve

Synopsis
--------

:program:`bkr workflow-reserve` [*workflow options*] [*options*]

Description
-----------

Generates a Beaker job for reserving a system.

If you have a specific system you want to reserve, pass its FQDN using the
:option:`--machine <bkr --machine>` option. Beaker will pick a suitable distro to provision
the system, or you can customize it by using the :option:`--arch <bkr --arch>`,
:option:`--family <bkr --family>`, or :option:`--distro <bkr --distro>` options.

If you don't know a specific system you want to reserve, pass :option:`--arch <bkr --arch>` and
:option:`--family <bkr --family>` or :option:`--distro <bkr --distro>` and let
Beaker's scheduler pick a suitable system. You can also narrow the system selection
by using various other workflow options, see :ref:`Workflow options <workflow-options>`.

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

To reserve a 64-bit ARM system and install Red Hat Enterprise Linux 7::

    bkr workflow-reserve --arch aarch64 --family RedHatEnterpriseLinux7

To reserve a specific system:

    bkr workflow-reserve --machine faultysystem.example.invalid

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client.task_watcher import *
from bkr.client import BeakerWorkflow, BeakerJob, BeakerRecipeSet, BeakerRecipe
import sys
import urllib
import xml.dom.minidom

class Workflow_Reserve(BeakerWorkflow):
    """Workflow to reserve a system"""
    enabled = True
    doc = xml.dom.minidom.Document()

    def options(self):
        super(Workflow_Reserve, self).options()
        # remove --task options
        self.parser.remove_option("--task")
        self.parser.remove_option("--taskfile")
        self.parser.remove_option("--task-type")
        self.parser.remove_option("--install")
        self.parser.remove_option("--kdump")
        self.parser.remove_option("--ndump")
        self.parser.remove_option("--suppress-install-task")
        # remove multihost options
        self.parser.remove_option("--clients")
        self.parser.remove_option("--servers")
        self.parser.usage = "%%prog %s [options]" % self.normalized_name

    def default_distro_tree(self, machine):
        if not hasattr(self, '_default_distro_tree'):
            requests_session = self.requests_session()
            response = requests_session.get('systems/%s/' % urllib.quote(machine, ''),
                                            headers={'Accept': 'application/json'})
            response.raise_for_status()
            distro_tree = response.json().get('default_distro_tree')
            if not distro_tree:
                sys.stderr.write("Could not find an appropriate distro to provision system with.")
                sys.exit(1)
            self._default_distro_tree = distro_tree
        return self._default_distro_tree

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)

        debug  = kwargs.get("debug", False)
        dryrun = kwargs.get("dryrun", False)
        wait = kwargs.get("wait", False)
        family = kwargs.get("family", None)
        distro = kwargs.get("distro", None)
        machine = kwargs.get("machine", None)
        arches = kwargs.get("arches", [])
        if machine:
            kwargs['ignore_system_status'] = True
            if not arches:
                arches = [self.default_distro_tree(machine)['arch']]
            if not family and not distro:
                kwargs['distro'] = self.default_distro_tree(machine)['distro']['name']
        else:
            if not family and not distro:
                sys.stderr.write("No Family or Distro specified\n")
                sys.exit(1)
            # defaults to 'x86_64' instead of all the known arches
            if not arches:
                arches = ['x86_64']
        kwargs['reserve'] = True

        # Create Job
        job = BeakerJob(*args, **kwargs)

        # Create Base Recipe
        recipeTemplate = BeakerRecipe()

        # Add Distro Requirements
        recipeTemplate.addBaseRequires(*args, **kwargs)

        for arch in arches:
            arch_node = self.doc.createElement('distro_arch')
            arch_node.setAttribute('op', '=')
            arch_node.setAttribute('value', arch)
            recipeSet = BeakerRecipeSet(**kwargs)
            recipeSet.addRecipe(self.processTemplate(recipeTemplate,
                                                     [],
                                                     distroRequires=arch_node,
                                                     **kwargs))
            job.addRecipeSet(recipeSet)

        # jobxml
        jobxml = job.toxml(**kwargs)
        if debug:
            print jobxml
        if not dryrun:
            try:
                job = self.hub.jobs.upload(jobxml)
                print "Submitted: %s" % job
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, ex:
                sys.stderr.write('Exception: %s\n' % ex)
                sys.exit(1)
            if wait:
                sys.exit(watch_tasks(self.hub, [job]))
