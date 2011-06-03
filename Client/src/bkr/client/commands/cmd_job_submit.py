# -*- coding: utf-8 -*-


from bkr.client.task_watcher import *
from bkr.client.convert import Convert
from bkr.client import BeakerCommand
from optparse import OptionValueError
import lxml.etree
import pkg_resources
import sys
import xml.dom.minidom

def combineTag(olddoc, newdoc, tag_name):
    # Take the tag from the first olddoc and add it to the newdoc.
    tags = olddoc.getElementsByTagName(tag_name)
    if tags and not newdoc.getElementsByTagName(tag_name):
        newdoc.appendChild(tags[0])

def combineAttr(olddoc, newdoc, attr_name):
    # Take the attr from the first olddoc and set it to the newdoc.
    if attr_name not in newdoc._attrs and attr_name in olddoc._attrs:
        newdoc.setAttribute(attr_name, olddoc.getAttribute(attr_name))

class Job_Submit(BeakerCommand):
    """Submit job(s) to scheduler"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <jobxml>..." % self.normalized_name
        self.parser.add_option(
            "--debug",
            default=False,
            action="store_true",
            help="print the jobxml that it would submit",
        )
        self.parser.add_option(
            "--dryrun",
            default=False,
            action="store_true",
            help="Don't submit job to scheduler",
        )
        self.parser.add_option(
            "--convert",
            default=False,
            action="store_true",
            help="convert from legacy rhts xml to beaker xml",
        )
        self.parser.add_option(
            "--combine",
            default=False,
            action="store_true",
            help="combine multiple jobs into one job",
        )
        self.parser.add_option(
            "--wait",
            default=False,
            action="store_true",
            help="wait on job completion",
        )
        self.parser.add_option(
            '--ignore-missing-tasks', default=False, action='store_true',
            help='silently discard tasks which do not exist on the scheduler',
        )

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        convert  = kwargs.pop("convert", False)
        combine  = kwargs.pop("combine", False)
        debug   = kwargs.pop("debug", False)
        dryrun  = kwargs.pop("dryrun", False)
        wait  = kwargs.pop("wait", False)
        ignore_missing_tasks = kwargs.pop('ignore_missing_tasks', False)

        jobs = args
        job_schema = lxml.etree.RelaxNG(lxml.etree.parse(
                pkg_resources.resource_stream('bkr.common', 'schema/beaker-job.rng')))

        self.set_hub(username, password)
        submitted_jobs = []
        failed = False

        # Read in all jobs.
        jobxmls = []
        for job in jobs:
            if job == '-':
                mystring = sys.stdin.read()
            else:
                mystring = open(job, "r").read()
            try:
                doc = xml.dom.minidom.parseString(mystring)
            except xml.parsers.expat.ExpatError:
                doc = xml.dom.minidom.parseString("<dummy>%s</dummy>" % mystring)
            # Split on jobs.
            for jobxml in doc.getElementsByTagName("job"):
                jobxmls.append(jobxml.toxml())

        # Combine into one job if requested.
        if combine:
            combined = xml.dom.minidom.Document().createElement("job")
            for jobxml in jobxmls:
                doc = xml.dom.minidom.parseString(jobxml)
                combineTag(doc,combined,"whiteboard")
                combineTag(doc,combined,"notify")
                combineAttr(doc.getElementsByTagName("job")[0], combined, "retention_tag")
                combineAttr(doc.getElementsByTagName("job")[0], combined, "product")
                # Add all recipeSet(s) to combined job.
                for recipeSet in doc.getElementsByTagName("recipeSet"):
                    combined.appendChild(recipeSet)
            # Set jobxmls to combined job.
            jobxmls = [combined.toxml()]

        # submit each job to scheduler
        for jobxml in jobxmls:
            if convert:
                jobxml = Convert.rhts2beaker(jobxml)
            if debug:
                print jobxml
            try:
                job_schema.assertValid(lxml.etree.fromstring(jobxml))
            except Exception, e:
                print >>sys.stderr, 'WARNING: job xml validation failed: %s' % e
            if not dryrun:
                try:
                    submitted_jobs.append(self.hub.jobs.upload(jobxml, ignore_missing_tasks))
                except Exception, ex:
                    failed = True
                    print ex
        if not dryrun:
            print "Submitted: %s" % submitted_jobs
            if wait:
                TaskWatcher.watch_tasks(self.hub, submitted_jobs)
            if failed:
                sys.exit(1)
