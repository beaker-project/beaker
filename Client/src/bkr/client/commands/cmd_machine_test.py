# -*- coding: utf-8 -*-


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
        self.parser.remove_option("--keyvalue")
        self.parser.remove_option("--distro")
        # Re-add option Family with append options
        self.parser.add_option(
            "--family",
            action="append",
            default=[],
            help="Test machine with this family",
        )
        self.parser.usage = "%%prog %s [options]" % self.normalized_name

    def run(self, *args, **kwargs):
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        self.set_hub(username, password)

        # get all tasks requested
        requestedTasks = ['/distribution/inventory']
        requestedTasks.extend(self.getTasks(*args, **kwargs))

        debug  = kwargs.get("debug", False)
        dryrun = kwargs.get("dryrun", False)
        wait = kwargs.get("wait", False)
        machine = kwargs.get("machine", None)
	families = kwargs.get("family", [])
	taskParams = kwargs.get("taskparam", [])

        if not machine:
            sys.stderr.write("No Machine Specified\n")
            sys.exit(1)

        if not kwargs.get("whiteboard"):
            kwargs["whiteboard"] = "Test %s" % machine

        if not families:
            try:
                families = self.getOsMajors(*args, tag=u'Active')
            except:
                families = ['RedHatEnterpriseLinux3',
                            'RedHatEnterpriseLinux4',
                            'RedHatEnterpriseLinuxClient5',
                            'RedHatEnterpriseLinuxServer5',
                            'RedHatEnterpriseLinux6',
                           ]

        # Create Job
        job = BeakerJob(*args, **kwargs)

        for family in families:
            if kwargs['arch']:
                arches = set(kwargs['arch']).intersection(set(self.getArches(family=family)))
            else:
               arches = self.getArches(family=family)
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
                print ex
        if not dryrun:
            print "Submitted: %s" % submitted_jobs
            if wait:
                TaskWatcher.watch_tasks(self.hub, submitted_jobs)
            if failed:
                sys.exit(1)
