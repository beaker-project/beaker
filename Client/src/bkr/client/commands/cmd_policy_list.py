
"""
.. _bkr-policy-list:

bkr policy-list: Lists access policy rules for a system
=======================================================

.. program:: bkr policy-list

Synopsis
--------

| :program:`bkr policy-list` [*options*] --system=<fqdn>

Description
-----------

Retrieves and prints the access policy rules for a system.

(Note: this command requires Python 2.6 or later)

Options
-------

.. option:: --system <fqdn>

   Retrieve the access policy for <fqdn>. This option must be specified exactly once.

.. option:: --format tabular, --format json

   Display results in the given format. The ``tabular`` format lists one rule per
   row as a table. This is the default. The ``json`` format returns the rules as a
   JSON string and is compact.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List current policy list for a system::

    bkr policy-list --system test1.example.com

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-policy-list(1)`
"""

import urllib
import pprint
from bkr.client import BeakerCommand
import bkr.client.json_compat as json
from prettytable import PrettyTable


class Policy_List(BeakerCommand):
    """Retrieves policy list"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options>" % self.normalized_name
        self.parser.add_option('--system', metavar='FQDN',
                               help='List access policy for FQDN')
        self.parser.add_option('--format',
                               type='choice',
                               choices=['tabular', 'json'],
                               default='tabular',
                               help='Display results in FORMAT: '
                               'tabular, json [default: %default]')

    def run(self, *args, **kwargs):

        system = kwargs.get('system', None)
        format = kwargs['format']

        if args:
            self.parser.error('This command does not accept any arguments')
        if not system:
            self.parser.error('Specify system using --system')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        rules_url = 'systems/%s/access-policy' % urllib.quote(system, '')
        res = requests_session.get(rules_url)
        res.raise_for_status()

        if format == 'json':
            print res.text
        else:
            policy_dict = json.loads(res.text)
            # setup table
            table = PrettyTable(['Permission', 'User', 'Group', 'Everybody'])
            for rule in policy_dict['rules']:
                everybody_humanreadble = 'Yes' if rule['everybody'] else 'No'
                table.add_row([col if col else 'X' for col in [rule['permission'],
                                                               rule['user'], rule['group'],
                                                               everybody_humanreadble]])
            print table.get_string(sortby='Permission')
