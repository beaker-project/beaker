# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr job-delete: Delete Beaker jobs
==================================

.. program:: bkr job-delete

Synopsis
--------

Delete specific jobs:

| :program:`bkr job-delete` [*options*] [--dryrun] <taskspec>...

Delete by criteria:

| :program:`bkr job-delete` [*options*] [--dryrun]
|       [:option:`--family` <family>] [:option:`--tag` <tag>] [:option:`--product` <cpeid>] [:option:`--completeDays` <days>]

Description
-----------

Specify one or more <taskspec> arguments to be deleted.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Only jobs may be deleted.

Options
-------

This command accepts the same options for selecting jobs as :program:`bkr 
job-list` does. See the :ref:`Options <job-list-options>` section of 
:manpage:`bkr-job-list(1)`.

.. option:: --dryrun

   Do not perform any deletions.

.. option:: --family <family>

   Delete jobs which ran with distro belonging to <family>, for example
   ``RedHatEnterpriseLinuxServer5``.

.. option:: --completeDays <days>

   Delete jobs which finished at least <days> ago.

.. option:: --tag <tag>

   Delete jobs which have retention tag <tag>, for example ``scratch``.

.. option:: --product <cpeid>

   Delete jobs which were testing the product identified by <cpeid>.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Delete all scratch jobs which finished 30 or more days ago:

    bkr job-delete --tag scratch --completeDays 30

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Job_Delete(BeakerCommand):
    """
    Delete Jobs in Beaker
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option(
            "-f",
            "--family",
            help="Family for which the Job is run against"
        )

        self.parser.add_option(
            "-t",
            "--tag",
            action="append",
            help="Jobs with a particular Tag"
        )

        self.parser.add_option(
            "-p",
            "--product",
            action="append",
            help="Jobs that are designated for a particular product"
        )
        """
        self.parser.add_option(
            "-u",
            "--userDeleted",
            default=False,
            dest='user_deleted',
            action='store_true',
            help="Currently not implemented"
        )
        """
        self.parser.add_option(
            "--dryrun",
            default=False,
            action="store_true",
            help="Test the likely output of job-delete without deleting anything",
        )

        self.parser.add_option(
            "-c",
            "--completeDays",
            type='int',
            help="Number of days it's been complete for"
        )

        """
        Currently not implemented: Allow degrees of deleteion
        self.parser.add_option(
            "-a",
            "--max-removal",
            action="store_const",
            const=0,
            default = False,
            dest="remove_all",
            help="Remove as much as server will allow us",
        )
        """

    def run(self, *args, **kwargs):
        tag = kwargs.pop('tag', None)
        product = kwargs.pop('product', None)
        complete_days = kwargs.pop('completeDays', None)
        family = kwargs.pop('family', None)
        dryrun = kwargs.pop('dryrun', None)
        # FIXME This is only useful for admins, will enable when we have the admin delete fucntionality
        """
        if user_deleted is True:
            if complete_days or tag or family or product or len(args) > 0:
                self.parser.error('You can only specify --userDeleted with no other flags')
        """

        if complete_days is not None and complete_days < 1:
            self.parser.error('Please pass a positive integer to completeDays')

        if (len(args) < 1
                and tag is None
                and complete_days is None
                and family is None
                and product is None
        ):
            self.parser.error('Please specify either a job, recipeset, tag, family, product or '
                              'complete days')
        if len(args) > 0:
            if (tag is not None
                    or complete_days is not None
                    or family is not None
                    or product is not None
            ):
                self.parser.error('Please either delete by job or tag/complete/family/product, '
                                  'not by both')
            self.check_taskspec_args(args, permitted_types=['J'])

        self.set_hub(**kwargs)
        jobs = []
        if args:
            for job in args:
                jobs.append(job)
        print(self.hub.jobs.delete_jobs(jobs, tag, complete_days, family, dryrun, product))
