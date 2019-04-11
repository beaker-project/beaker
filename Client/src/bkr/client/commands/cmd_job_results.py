# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr job-results: Export Beaker job results as XML
=================================================

.. program:: bkr job-results

Synopsis
--------

:program:`bkr job-results` [--prettyxml] [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be exported. An XML dump of the 
results for each argument will be printed to stdout.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Options
-------

.. option:: --format <format>

   Shows results in the given format.
   The ``beaker-results-xml`` format (default) is a superset of the Beaker job 
   definition XML syntax.
   The ``junit-xml`` format is compatible with the Ant JUnit runner's XML 
   output and is understood by Jenkins, Eclipse, and other tools.

.. option:: --prettyxml

   Pretty-print the Beaker results XML (with indentation and line breaks, 
   suitable for human consumption).
   JUnit XML is always pretty-printed regardless of this option.

.. option:: --no-logs

   Since Beaker 24.0, the results include links to all logs when using the 
   ``beaker-results-xml`` format. This can substantially increase the size of 
   the XML. Use this option to omit the logs (matching the behaviour of 
   previous Beaker versions).

   JUnit XML always includes logs regardless of this option.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Display results for job 12345 in human-readable form (assuming the human can 
read XML)::

    bkr job-results --prettyxml J:12345

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import lxml.etree
import six

from bkr.client import BeakerCommand


class Job_Results(BeakerCommand):
    """
    Get Jobs/Recipes Results
    """
    enabled = True
    requires_login = False

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name
        self.parser.add_option(
            '--format',
            type='choice', choices=['beaker-results-xml', 'junit-xml'],
            default='beaker-results-xml',
            help='Display results in this format: '
                 'beaker-results-xml, junit-xml [default: %default]',
        )
        self.parser.add_option(
            "--prettyxml",
            default=False,
            action="store_true",
            help="Pretty print the xml",
        )
        self.parser.add_option(
            '--no-logs',
            dest='include_logs', action='store_false', default=True,
            help='Omit logs from results XML',
        )

    def run(self, *args, **kwargs):
        self.check_taskspec_args(args)

        format = kwargs.pop("format")
        prettyxml = kwargs.pop("prettyxml", None)
        include_logs = kwargs.pop('include_logs')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        for task in args:
            if format == 'beaker-results-xml':
                myxml = self.hub.taskactions.to_xml(task, False, True, include_logs)
                # XML is really bytes, the fact that the server is sending the bytes as an
                # XML-RPC Unicode string is just a mistake in Beaker's API
                myxml = myxml.encode('utf8')
                str_xml = lxml.etree.tostring(lxml.etree.fromstring(myxml),
                                              pretty_print=prettyxml,
                                              xml_declaration=prettyxml,
                                              encoding='utf-8')
                if six.PY3:  # Decode bytes to string (otherwise print will be broken)
                    str_xml = str_xml.decode('utf-8')
                print(str_xml)
            elif format == 'junit-xml':
                type, colon, id = task.partition(':')
                if type != 'J':
                    self.parser.error('JUnit XML format is only available for jobs')
                response = requests_session.get('jobs/%s.junit.xml' % id)
                response.raise_for_status()
                print(response.content)
            else:
                raise RuntimeError('Format %s not implemented' % format)
