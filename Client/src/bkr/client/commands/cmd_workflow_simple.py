# -*- coding: utf-8 -*-


from bkr.client.task_watcher import *
from bkr.client import BeakerCommand, BeakerWorkflow, BeakerJob, BeakerRecipe
from optparse import OptionValueError
import sys
import xml.dom.minidom
import copy

class Workflow_Simple(BeakerWorkflow):
    """Simple workflow to generate job to scheduler"""
    enabled = True
    doc = xml.dom.minidom.Document()

    def options(self):
        super(Workflow_Simple, self).options()
        self.parser.usage = "%%prog %s [options] <task> <task>" % self.normalized_name

    def run(self, *args, **kwargs):
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)

        # get all tasks requested
        requestedTasks = self.getTasks(*args, **kwargs)

        debug   = kwargs.get("debug", False)
        dryrun  = kwargs.get("dryrun", False)
        nowait  = kwargs.get("nowait", False)
	family = kwargs.get("family", None)
	distro = kwargs.get("distro", None)
	arches = kwargs.get("arch", [])
	taskParams = kwargs.get("taskparam", [])

        if not family and not distro:
            sys.stderr.write("No Family or Distro specified\n")
            sys.exit(1)

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

        # Add tasks that have been requested
        for task in requestedTasks:
            recipeTemplate.addTask(task, taskParams=taskParams)

        for arch in arches:
            # Copy basic requirements
            recipe = copy.deepcopy(recipeTemplate)

            arch_node = self.doc.createElement('distro_arch')
            arch_node.setAttribute('op', '=')
            arch_node.setAttribute('value', arch)
            recipe.addDistroRequires(arch_node)

            job.addRecipe(recipe)


        # jobxml
        jobxml = job.toxml()

        if debug:
            print jobxml

        self.set_hub(username, password)
        submitted_jobs = []
        failed = False

        if not dryrun:
            try:
                submitted_jobs.append(self.hub.jobs.upload(jobxml))
            except Exception, ex:
                failed = True
                print ex
        if not dryrun:
            if not nowait:
                TaskWatcher.watch_tasks(self.hub, submitted_jobs)
            for submitted_job in submitted_jobs:
                print self.hub.taskactions.to_xml(submitted_job)
            if failed:
                sys.exit(1)
