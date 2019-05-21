
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr system-details: Export RDF/XML description of a Beaker system
=================================================================

.. program:: bkr system-details

Synopsis
--------

:program:`bkr system-details` [*options*] <fqdn>
|    [:option:'--format' <json_or_xml>]

Description
-----------

Prints to stdout an RDF/XML description of the given system.

A copy of the Beaker RDF schema definition is installed as
:file:`/usr/lib/python2.{x}/bkr/common/schema/beaker-inventory.ttl`.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Export RDF/XML for a particular system::

    bkr system-details system1.example.invalid

Display details of a system in JSON format::

    bkr system-details --format json system1.example.invalid

See also
--------

:manpage:`bkr-system-list(1)`, :manpage:`bkr(1)`
"""

from __future__ import print_function

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class System_Details(BeakerCommand):
    """
    Export RDF/XML description of a system
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name
        self.parser.add_option('--format',
                               type='choice',
                               choices=['json', 'xml'],
                               default='xml',
                               help='Display results in FORMAT: '
                               'json, xml [default: %default]')

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]
        format = kwargs.get('format')

        if format == 'json':
            system_url = 'systems/%s/' % parse.quote(fqdn, '')
        else:
            system_url = 'view/%s?tg_format=rdfxml' % parse.quote(fqdn, '')

        # This will log us in using XML-RPC
        self.set_hub(**kwargs)

        session = self.requests_session()
        response = session.get(system_url)
        response.raise_for_status()
        print(response.text)
