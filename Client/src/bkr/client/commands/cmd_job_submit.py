# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr job-submit: Submit job XML to Beaker
========================================

.. program:: bkr job-submit

Synopsis
--------

| :program:`bkr job-submit` [*options*]
|       [--debug] [--convert] [--combine] [--ignore-missing-tasks]
|       [:option:`--dry-run` | :option:`--wait`]
|       [<filename>...]

Description
-----------

Reads Beaker job XML descriptions and submits them to Beaker.

Specify one or more filenames containing job XML to be submitted. If multiple 
filenames are given, each one is submitted as a separate job. If no filenames 
are given, job XML is read from stdin. The special filename '-' also reads from 
stdin.

Options
-------

.. option:: --debug

   Legacy option, replaced by '--xml'

.. option:: --xml

   Print the job XML before submitting it.

.. option:: --convert

   Attempt to convert legacy RHTS XML to Beaker XML. Use this with 
   :option:`--xml` and :option:`--dry-run` to grab the converted XML without
   submitting it.

.. option:: --combine

   If more than one job XML argument is given, the recipe sets from each job 
   are extracted and combined into a single job before submission.

.. option:: --ignore-missing-tasks

   If the job refers to tasks which are not known to the scheduler, silently 
   discard these from the recipe. Normally this is a fatal error which prevents 
   submission of the job.

.. option:: --dry-run

   Do not submit the job(s) to Beaker. Use this with :option:`--xml` to see 
   what would be submitted.

.. option:: --wait

   Watch the newly submitted jobs for state changes and print them to stdout. 
   The command will not exit until all submitted jobs have finished. See 
   :manpage:`bkr-job-watch(1)`.

.. option:: --job-owner <username>

   Submit the job on behalf of <username>. The submitted job will be owned by
   <username> rather than the submitting user.

   The existing user attribute in the job XML will be overridden if set.

   The submitting user must be a submission delegate of <username>. Users can
   add other users as submission delegates on their :guilabel:`Preferences`
   page in Beaker's web UI.

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

from __future__ import print_function

import sys
import xml.dom.minidom

import lxml.etree
import pkg_resources
import six

from bkr.client import BeakerCommand
from bkr.client.convert import Convert
from bkr.client.task_watcher import *


def combine_tag(olddoc, newdoc, tag_name):
    # Take the tag from the first olddoc and add it to the newdoc.
    tags = olddoc.getElementsByTagName(tag_name)
    if tags and not newdoc.getElementsByTagName(tag_name):
        newdoc.appendChild(tags[0])


combineTag = combine_tag


def combine_attr(olddoc, newdoc, attr_name):
    # Take the attr from the first olddoc and set it to the newdoc.
    # py3 _attrs are None instead of {}
    if (newdoc._attrs is None or attr_name not in newdoc._attrs
            and (olddoc._attrs and attr_name in olddoc._attrs)):
        newdoc.setAttribute(attr_name, olddoc.getAttribute(attr_name))


combineAttr = combine_attr


class Job_Submit(BeakerCommand):
    """
    Submit job(s) to scheduler
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <jobxml>..." % self.normalized_name
        self.parser.description = """\
Specify one or more filenames containing job XML to be submitted. If multiple
filenames are given, each one is submitted as a separate job. If no filenames
are given, job XML is read from stdin. The special filename '-' also reads from
stdin."""
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
            "--dry-run", "--dryrun",
            dest="dryrun",
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
        self.parser.add_option(
             '--job-owner', metavar='USERNAME',
             help='Submit job on behalf of USERNAME. '
                  'The existing user attribute in the job XML will be overridden if set. '
                  '(submitting user must be a submission delegate for job owner)',
        )

    def run(self, *args, **kwargs):
        convert  = kwargs.pop("convert", False)
        combine  = kwargs.pop("combine", False)
        debug   = kwargs.pop("debug", False)
        print_xml = kwargs.pop("xml", False)
        dryrun  = kwargs.pop("dryrun", False)
        wait  = kwargs.pop("wait", False)
        ignore_missing_tasks = kwargs.pop('ignore_missing_tasks', False)
        job_owner = kwargs.pop("job_owner", None)

        jobs = args
        if not jobs:
            jobs = ['-'] # read one job from stdin by default
        job_schema = lxml.etree.RelaxNG(lxml.etree.parse(
                pkg_resources.resource_stream('bkr.common', 'schema/beaker-job.rng')))

        self.set_hub(**kwargs)
        submitted_jobs = []
        is_failed = False

        # Read in all jobs.
        jobxmls = []
        for job in jobs:
            if job == '-':
                if six.PY3:  # Handle piped non UTF-8 data
                    with open(0, 'rb') as f:
                        mystring = f.read()
                else:
                    mystring = sys.stdin.read()
            else:
                mystring = open(job, "r").read()
            try:
                doc = xml.dom.minidom.parseString(mystring)
            except xml.parsers.expat.ExpatError:
                doc = xml.dom.minidom.parseString("<dummy>%s</dummy>" % mystring)
            # Split on jobs.
            for jobxml in doc.getElementsByTagName("job"):
                if job_owner is not None:
                    jobxml.setAttribute('user', job_owner)
                jobxmls.append(jobxml.toxml())

        # Combine into one job if requested.
        if combine:
            combined = xml.dom.minidom.Document().createElement("job")
            for jobxml in jobxmls:
                doc = xml.dom.minidom.parseString(jobxml)
                combine_tag(doc, combined, "whiteboard")
                combine_tag(doc, combined, "notify")
                combine_attr(doc.getElementsByTagName("job")[0], combined, "retention_tag")
                combine_attr(doc.getElementsByTagName("job")[0], combined, "product")
                combine_attr(doc.getElementsByTagName("job")[0], combined, "user")
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
                print(jobxml)
            try:
                job_schema.assertValid(lxml.etree.fromstring(jobxml))
            except Exception as e:
                sys.stderr.write('WARNING: job xml validation failed: %s\n' % e)
            if not dryrun:
                try:
                    submitted_jobs.append(self.hub.jobs.upload(jobxml, ignore_missing_tasks))
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as ex:
                    is_failed = True
                    sys.stderr.write('Exception: %s\n' % ex)
        if not dryrun:
            print("Submitted: %s" % submitted_jobs)
            if wait:
                is_failed |= watch_tasks(self.hub, submitted_jobs)
        sys.exit(is_failed)

