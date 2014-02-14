# -*- coding: utf-8 -*-

"""
bkr job-submit: Submit job XML to Beaker
========================================

.. program:: bkr job-submit

Synopsis
--------

| :program:`bkr job-submit` [*options*]
|       [--debug] [--convert] [--combine] [--ignore-missing-tasks]
|       [:option:`--dryrun` | :option:`--wait`] <jobxml>...

Description
-----------

Specify one or more <jobxml> filenames to be submitted to Beaker. Pass '-' to 
read from stdin.

Options
-------

.. option:: --debug

   Legacy option, replaced by '--xml'

.. option:: --xml

   Print the job XML before submitting it.

.. option:: --convert

   Attempt to convert legacy RHTS XML to Beaker XML. Use this with 
   :option:`--xml` and :option:`--dryrun` to grab the converted XML without 
   submitting it.

.. option:: --combine

   If more than one job XML argument is given, the recipe sets from each job 
   are extracted and combined into a single job before submission.

.. option:: --ignore-missing-tasks

   If the job refers to tasks which are not known to the scheduler, silently 
   discard these from the recipe. Normally this is a fatal error which prevents 
   submission of the job.

.. option:: --dryrun

   Do not submit the job(s) to Beaker. Use this with :option:`--xml` to see 
   what would be submitted.

.. option:: --wait

   Watch the newly submitted jobs for state changes and print them to stdout. 
   The command will not exit until all submitted jobs have finished. See 
   :manpage:`bkr-job-watch(1)`.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

1 if any jobs failed submission or execution, otherwise zero.

Examples
--------

Submit a job and watch its progress on stdout::

    bkr job-submit --wait my-beaker-job.xml

See also
--------

:manpage:`bkr(1)`
"""


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
        # This is now just legacy, --xml is the more accurate term
        self.parser.add_option(
            "--debug",
            default=False,
            action="store_true",
            help="Alias for the --xml option",
        )
        self.parser.add_option(
            "--xml",
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
        convert  = kwargs.pop("convert", False)
        combine  = kwargs.pop("combine", False)
        debug   = kwargs.pop("debug", False)
        print_xml = kwargs.pop("xml", False)
        dryrun  = kwargs.pop("dryrun", False)
        wait  = kwargs.pop("wait", False)
        ignore_missing_tasks = kwargs.pop('ignore_missing_tasks', False)

        jobs = args
        job_schema = lxml.etree.RelaxNG(lxml.etree.parse(
                pkg_resources.resource_stream('bkr.common', 'schema/beaker-job.rng')))

        self.set_hub(**kwargs)
        submitted_jobs = []
        is_failed = False

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
            if debug or print_xml:
                print jobxml
            try:
                job_schema.assertValid(lxml.etree.fromstring(jobxml))
            except Exception, e:
                sys.stderr.write('WARNING: job xml validation failed: %s\n' % e)
            if not dryrun:
                try:
                    submitted_jobs.append(self.hub.jobs.upload(jobxml, ignore_missing_tasks))
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception, ex:
                    is_failed = True
                    sys.stderr.write('Exception: %s\n' % ex)
        if not dryrun:
            print "Submitted: %s" % submitted_jobs
            if wait:
                if self.conf.get('QPID_BUS') is True:
                    if self.conf.get('AUTH_METHOD' != 'krbv'):
                        print 'Cannot wait for task, Please set AUTH_METHOD to \'krbv\' when listening via message bus'
                    else:
                        is_failed |= watch_bus_tasks(0, submitted_jobs)
                else:
                    is_failed |= watch_tasks(self.hub, submitted_jobs)
        sys.exit(is_failed)

