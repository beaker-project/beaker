# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-update-inventory:

bkr update-inventory: Submits a inventory job for the system
============================================================

.. program:: bkr update-inventory

Synopsis
--------

|  :program:`bkr update-inventory` [*options*]
|       [:option:`--xml` | :option:`--pretty-xml`]
|       [:option:`--dry-run` | :option:`--wait`]
|       [<fqdn>...]

Description
-----------

Submits a job to scan the given system and update its hardware
details recorded in Beaker. The Beaker server will automatically
select the most suitable distro tree based on the system's
architecture and the availability of the distro trees.

If you want to customize the distro selection or add other tasks
to the job, use :option:`bkr machine-test --inventory` instead.
That command supports the complete set of workflow options for
customizing your job.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.


.. versionadded:: 21

Options
-------

.. option:: --xml

   Print the generated Job XML that was submitted. Use this with
   :option:`--dry-run` if you just want to see what would be submitted.

.. option:: --pretty-xml

   Pretty print the generated Job XML that was submitted. Use this with
   :option:`--dry-run` if you just want to see what would be submitted.

.. option:: --dry-run

   Do not submit the job(s) to Beaker. Use this with :option:`--xml`
   or :option:`--pretty-xml` to see what would be submitted.

.. option:: --wait

   Watch the newly submitted jobs for state changes and print them to stdout.
   The command will not exit until all submitted jobs have finished. See
   :manpage:`bkr-job-watch(1)`.

Exit status
-----------

1 if any jobs failed submission or execution (when --wait is used), otherwise zero.

Examples
--------

Submit an inventory job for test1.example.com::

   bkr update-inventory test1.example.com

Do not submit an inventory job, but just pretty print the generated job XML::

   bkr update-inventory --dry-run --pretty-xml test1.example.com


See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-machine-test(1)`,
"""

from __future__ import print_function

import cgi
import sys
from xml.dom.minidom import parseString

from requests.exceptions import HTTPError

from bkr.client import BeakerCommand
from bkr.client.task_watcher import watch_tasks


class Update_Inventory(BeakerCommand):
    """
    Submits a Inventory job
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <fqdn>.." % self.normalized_name
        self.parser.add_option(
            '--dry-run', '--dryrun',
            default=False,
            action='store_true',
            dest='dryrun',
            help='Do not submit an inventory job',
        )
        self.parser.add_option(
            '--xml',
            default=False,
            action='store_true',
            help='Print the generated Job XML',
        )
        self.parser.add_option(
            '--pretty-xml', '--prettyxml',
            dest='prettyxml',
            default=False,
            action='store_true',
            help='Pretty print the generated Job XML',
        )
        self.parser.add_option(
            '--wait',
            default=False,
            action='store_true',
            help='Wait on job completion',
        )

    def run(self, *args, **kwargs):

        if not args:
            self.parser.error('One or more systems must be specified')
        dryrun = kwargs.get('dryrun')
        xml = kwargs.get('xml')
        prettyxml = kwargs.get('prettyxml')
        wait = kwargs.get('wait')
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        submitted_jobs = []
        failed = False
        for fqdn in args:
            res = requests_session.post('jobs/+inventory',
                                        json={'fqdn': fqdn,
                                              'dryrun': dryrun})
            try:
                res.raise_for_status()
            except HTTPError as e:
                sys.stderr.write('HTTP error: %s, %s\n' % (fqdn, e))
                content_type, _ = cgi.parse_header(e.response.headers.get(
                    'Content-Type', ''))
                if content_type == 'text/plain':
                    sys.stderr.write('\t' +
                                     e.response.content.rstrip('\n') +
                                     '\n')
                failed = True
            else:
                res_data = res.json()
                if xml:
                    print(res_data['job_xml'])
                if prettyxml:
                    print(parseString(res_data['job_xml']).toprettyxml(encoding='utf8'))
                if not dryrun:
                    submitted_jobs.append(res_data['job_id'])
        if not dryrun:
            print("Submitted: %s" % submitted_jobs)
            if wait:
                failed |= watch_tasks(self.hub, submitted_jobs)
            sys.exit(failed)
