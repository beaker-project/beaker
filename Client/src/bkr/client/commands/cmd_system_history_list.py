# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr system-history-list: Export history of activity for the given system
========================================================================

.. program:: bkr system-history-list

Synopsis
--------

| :program:`bkr system-history-list` [*options*] <fqdn>
|       [:option:`--pretty`]
|       [:option:`--since` <date>]



Description
-----------

JSON history of activity for a given system is printed to stdout.

.. versionadded:: 27

Options
-------

.. option:: --since <date>

    If the since option is given, all history entries between that
    timestamp and the present are returned. By default, history entries
    from the past 24 hours are returned. Date has to be defined in
    UTC format YYYY-MM-DD.

.. option:: --pretty

   Pretty-print results in JSON (with indentation and line breaks,
   suitable for human consumption).

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Display history of a system in JSON format from the past 24 hours:

    bkr system-history-list system1.example.invalid

Display history of a system in JSON format started from 2019-06-25:

    bkr system-history-list system1.example.invalid --since 2019-06-25

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import json

from datetime import datetime
from six.moves import xmlrpc_client

from bkr.client import BeakerCommand


def json_serial(obj):
    """
    JSON serializer for objects not serializable by default json code
    """
    if isinstance(obj, xmlrpc_client.DateTime):
        return obj.value
    raise TypeError("Type %s not serializable" % type(obj))


class System_History_List(BeakerCommand):
    """
    Export JSON history of activity of a system
    """
    enabled = True

    def check_valid_date(self, since):
        try:
            valid_since = datetime.strptime(since, '%Y-%m-%d')
        except ValueError:
            self.parser.error('Incorrect date format, should be YYYY-MM-DD')
        return valid_since

    def options(self):
        self.parser.usage = "%%prog %s <options> " % self.normalized_name
        self.parser.add_option('--since', action="store", type="string",
                               dest="since",
                               help="Start date defined in following format YYYY-MM-DD")
        self.parser.add_option("--pretty",
                               default=False,
                               action="store_true",
                               help="Pretty print the JSON output",
                               )

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system FQDN must be given')
        fqdn = args[0]
        since = kwargs.pop('since', None)
        pretty = kwargs.pop('pretty')
        since = since and self.check_valid_date(since)

        # This will log us in using XML-RPC
        self.set_hub(**kwargs)

        action_list = self.hub.systems.history(fqdn, since)
        print(json.dumps({i: action for i, action in enumerate(action_list)},
                         default=json_serial,
                         sort_keys=True,
                         indent=4 if pretty else None))
