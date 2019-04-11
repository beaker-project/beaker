# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr group-list: List groups
===========================

.. program:: bkr group-list

Synopsis
--------

| :program:`bkr group-list`
|       [:option:`--owner` <user>]
|       [:option:`--limit` <number>]

Description
-----------

Lists groups or groups owned by the given user.

Options
-------

.. option:: --owner <username>

   List groups owned by <username>.

.. option:: --limit <number>

   Return at most <number> groups. The default is 50.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List all groups which are owned by the user ``test``::

    bkr group-list --owner test

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-group-members(1)`

"""

from __future__ import print_function

import sys

from bkr.client import BeakerCommand


class Group_List(BeakerCommand):
    """
    List groups
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name

        self.parser.add_option('--owner',
                               metavar='USERNAME',
                               help='List groups owned by owner USERNAME')

        self.parser.add_option("--limit",
                               default=50,
                               type=int,
                               help='Limit results to this many [default: %default]')

    def run(self, *args, **kwargs):
        owner = kwargs.get('owner', None)
        limit = kwargs.get('limit')

        self.set_hub(**kwargs)

        requests_session = self.requests_session()

        params = {'page_size': limit}
        if owner:
            params['q'] = 'owner.user_name:%s' % owner

        response = requests_session.get('groups/', params=params, headers={'Accept': 'application/json'})

        response.raise_for_status()
        attributes = response.json()
        groups = attributes['entries']

        if not groups:
            sys.stderr.write('Nothing Matches\n')
            sys.exit(1)

        for group in groups:
            print(group['group_name'])
