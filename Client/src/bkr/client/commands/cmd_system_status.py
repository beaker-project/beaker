# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-system-status:

bkr system-status:  Return the current status of a system
=========================================================

.. program:: bkr system-status

Synopsis
--------

| :program:`bkr system-status` [*options*] <fqdn> --format <format>

Description
-----------

Prints to stdout the current status of a system whose FQDN is <fqdn>. This
includes the condition, current reservation details, and current loan details.

Options
-------

.. option:: --format <format>

   Display results in the given format, either ``tabular`` or ``json``.
   The ``tabular`` format is intended for human consumption, whereas the 
   ``json`` format is machine-readable. The default is ``tabular``.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Display the status of invalid.example.com in JSON format::

    bkr system-status invalid.example.com --format json

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from json import loads

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class System_Status(BeakerCommand):
    """
    Return the current status of a system
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options> <fqdn>" % self.normalized_name
        self.parser.add_option('--format',
                               type='choice',
                               choices=['tabular', 'json'],
                               default='tabular',
                               help='Display results in FORMAT: '
                                    'tabular, json [default: %default]')

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]
        format = kwargs.get('format')
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        status_url = 'systems/%s/status' % parse.quote(fqdn, '')
        res = requests_session.get(status_url)
        res.raise_for_status()
        if format == 'json':
            print(res.text)
        else:
            system_status = loads(res.text)
            condition = system_status.get('condition')
            reservation_details = system_status.get('current_reservation')
            msg = ['Condition: %s' % condition]
            if reservation_details:
                reserved_by = reservation_details.get('user_name')
                recipe_id = reservation_details.get('recipe_id')
                start_time = reservation_details.get('start_time')
                msg.append('Current reservation:')
                if reserved_by:
                    # The '%4s' % '' formatting is to indent the output
                    # and make it easier to read.
                    msg.append('%4sUser: %s' % ('', reserved_by))
                if recipe_id:
                    msg.append('%4sRecipe ID: %s' % ('', recipe_id))
                if start_time:
                    msg.append('%4sStart time: %s' % ('', start_time))
            else:
                msg.append('Current reservation: %s' % None)

            loan_details = system_status.get('current_loan')
            if loan_details:
                loaned_to = loan_details.get('recipient')
                loan_comment = loan_details.get('comment')
                msg.append('Current loan:')
                if loaned_to:
                    msg.append('%4sUser: %s' % ('', loaned_to))
                if loan_comment:
                    msg.append('%4sComment: %s' % ('', loan_comment))
            else:
                msg.append('Current loan: %s' % None)
            print('\n'.join(msg))
