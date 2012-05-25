
"""
List Beaker jobs
================

.. program:: bkr job-list

Synopsis
--------

| :program:`bkr job-list` [*options*]
|       [--family=<family>] [--tag=<tag>] [--product=<cpeid>] [--completeDays=<days>]

Description
-----------

Prints to stdout a list of matching Beaker jobs.

.. _job-list-options:

Options
-------

.. option:: --family <family>

   Limit to jobs which ran with distro belonging to <family>, for example 
   ``RedHatEnterpriseLinuxServer5``.

.. option:: --completeDays <days>

   Limit to jobs which finished at least <days> ago.

.. option:: --tag <tag>

   Limit to jobs which have retention tag <tag>, for example ``scratch``.

.. option:: --product <cpeid>

   Limit to jobs which were testing the product identified by <cpeid>.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List all scratch jobs which finished 30 or more days ago::

    bkr job-list --tag scratch --completeDays 30

See also
--------

:manpage:`bkr(1)`
"""

from bkr.client import BeakerCommand
from optparse import OptionValueError

class Job_List(BeakerCommand):
    """List Beaker jobs """
    enabled = True
    
    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option(
            "-f",
            "--family",
            help="Family for which the Job is run against"
        )

        self.parser.add_option(
            "-c",
            "--completeDays",
            type='int',
            help="Number of days job has been completed for"
        )

        self.parser.add_option(
            "-t",
            "--tag",
            action="append",
            help="Jobs with a particular tag"
        )

        self.parser.add_option(
            "-p",
            "--product", 
            help="Jobs for a particular product"
        )

    def run(self,*args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        family = kwargs.pop('family', None)
        tag = kwargs.pop('tag', None)
        product = kwargs.pop('product', None)
        complete_days = kwargs.pop('completeDays', None)

        if complete_days is not None and complete_days < 1:
            self.parser.error('Please pass a positive integer to completeDays')

        if complete_days is None and tag is None and family is None and product is None:
            self.parser.error('Please pass either the completeDays time delta, a tag, product or family')

        self.set_hub(username,password)
        jobs = []
        print self.hub.jobs.list(tag,complete_days,family,product)

