# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr job-modify: Modify Beaker jobs
==================================

.. program:: bkr job-modify

Synopsis
--------

| :program:`bkr job-modify` [*options*] <taskspec>
|       [:option:`--response` <response>] [:option:`--retention-tag` <retention_tag>]
|       [:option:`--product` <product>] [:option:`--priority` <priority>]


Description
-----------


Specify one or more <taskspec> arguments to be modified.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

.. _job-modify-options:

Options
-------

.. option:: --response <response>

   Sets the response type of the job. Can be either 'ack' or 'nak'.

.. option:: --retention-tag <retention_tag>

   Sets the retention tag of a job. Must coincide with correct product value.
   Please refer to the job page to see a list of available retention tags.

.. option:: --product <product>

   Sets the product of a job. Must co-incide with correct retention 
   tag value. Please refer to the job page to see a list of available 
   products.

.. option:: --priority <priority>

   Sets the priority. Recipe sets with higher priority are scheduled sooner by
   Beaker's scheduler. Only permitted for recipe sets and jobs which are queued.
   Valid priorities are: Low, Medium, Normal, High, Urgent.

.. option:: --whiteboard <whiteboard>

   Sets the whiteboard of a job or recipe. The whiteboard is a free-form string 
   to describe the job or recipe.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Set a recipe set to 'ack':

    bkr job-modify RS:1 --response ack

Set multiple jobs to be 'nak':

    bkr job-modify J:1 J:2 --response nak

Set a job's retention tag of 60days:

    bkr job-modify J:1 --retention-tag 60days

Set a job's product to validproduct and the audit retention tag:

   bkr job-modify J:1 --product validproduct --retention-tag audit

Unset a job's product and change to the scratch retention tag:

   bkr job-modify J:1 --retention-tag scratch --product=

Set a job's priority to 'High' which will apply to all the recipe sets in the job:

   bkr job-modify J:1 --priority High

Set a recipe set's priority to 'High':

   bkr job-modify RS:1 --priority High

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import sys

import requests
from six.moves.xmlrpc_client import Fault

from bkr.client import BeakerCommand


class Job_Modify(BeakerCommand):
    """
    Modify certain job properties
    """

    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec> ..." % self.normalized_name
        self.parser.add_option(
            "-r",
            "--response",
            help="Set a job or recipesets response. Valid values are 'ack' or 'nak'",
        )

        self.parser.add_option(
            "-t",
            "--retention-tag",
            help="Set a job's retention tag",
        )

        self.parser.add_option(
            "-p",
            "--product",
            help="Set a job's product",
        )

        self.parser.add_option(
            "--priority",
            type='choice',
            choices=['Low', 'Medium', 'Normal', 'High', 'Urgent'],
            help='Change job priority: Low, Medium, Normal, High, Urgent',
        )
        self.parser.add_option(
            '--whiteboard',
            help='Set job or recipe whiteboard',
        )

    def run(self, *args, **kwargs):
        response = kwargs.pop('response', None)
        retention_tag = kwargs.pop('retention_tag', None)
        product = kwargs.pop('product', None)
        priority = kwargs.pop('priority', None)
        whiteboard = kwargs.pop('whiteboard', None)

        self.set_hub(**kwargs)
        if response or priority:
            self.check_taskspec_args(args, permitted_types=['J', 'RS'])
        if retention_tag or product is not None:
            self.check_taskspec_args(args, permitted_types=['J'])
        if whiteboard:
            self.check_taskspec_args(args, permitted_types=['J', 'R'])
        modded = []
        error = False
        requests_session = self.requests_session()
        for taskspec in args:
            try:
                if response:
                    self.hub.jobs.set_response(taskspec, response)
                    modded.append(taskspec)
                if retention_tag or product is not None:
                    self.hub.jobs.set_retention_product(taskspec, retention_tag,
                                                        product, )
                    modded.append(taskspec)
                if priority:
                    res = requests_session.patch('recipesets/by-taskspec/%s'
                                                 % taskspec, json={'priority': priority.title()})
                    res.raise_for_status()
                    modded.append(taskspec)
                if whiteboard:
                    type, id = taskspec.split(':', 1)
                    if type == 'J':
                        res = requests_session.patch('jobs/%s' % id,
                                                     json={'whiteboard': whiteboard})
                        res.raise_for_status()
                    elif type == 'R':
                        res = requests_session.patch('recipes/%s' % id,
                                                     json={'whiteboard': whiteboard})
                        res.raise_for_status()
                    modded.append(taskspec)
            except (Fault, requests.HTTPError) as e:
                sys.stderr.write('Failed to modify %s: %s\n' % (taskspec, e))
                error = True
        if modded:
            modded = set(modded)
            print('Successfully modified jobs %s' % ' '.join(modded))
        else:
            print('No jobs modified')

        if error:
            sys.exit(1)
        else:
            sys.exit(0)
