# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-job-logs:

bkr job-logs: Print URLs of Beaker recipe log files
===================================================

.. program:: bkr job-logs

Synopsis
--------

:program:`bkr job-logs` [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be exported. A list of the 
log files for each argument will be printed to stdout.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Options
-------

.. option:: --size

   Print the file size (in bytes) alongside each log file URL.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Display logs for job 12345::

    bkr job-logs J:12345

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Job_Logs(BeakerCommand):
    """
    Print URLs of recipe log files
    """
    enabled = True
    requires_login = False

    def options(self):
        self.parser.add_option('--size', action='store_true',
                               help='Print file size alongside each log file')
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name

    def _log_size(self, url):
        response = self.session.head(url, allow_redirects=True)
        if response.status_code in (404, 410):
            return '<missing>'
        elif response.status_code >= 400:
            return '<error:%s>' % response.status_code
        try:
            return '%6d' % int(response.headers['Content-Length'])
        except ValueError:
            return '<invalid>'

    def run(self, *args, **kwargs):
        self.check_taskspec_args(args)

        self.set_hub(**kwargs)
        self.session = self.requests_session()
        for task in args:
            logfiles = self.hub.taskactions.files(task)
            for log in logfiles:
                if kwargs.get('size'):
                    print(self._log_size(log['url']), log['url'])
                else:
                    print(log['url'])
