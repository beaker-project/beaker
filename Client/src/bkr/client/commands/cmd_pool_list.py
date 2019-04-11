# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr pool-list: List system pools
================================

.. program:: bkr pool-list

Synopsis
--------

| :program:`bkr pool-list` [*options*]
|       [:option:`--owning-group` <groupname> | :option:`--owner` <user>]
|       [:option:`--limit` <number>]

Description
-----------

Lists pools.

Options
-------

.. option:: --owning-group <groupname>

   List pools owned by <groupname>

.. option:: --owner <username>

   List pools owned by <username>

.. option:: --limit <number>

   Return at most <number> pools.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List all pools which are owned by the ``beakerdevs`` group::

    bkr pool-list --owning-group beakerdevs

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-pool-systems(1)`

"""

from __future__ import print_function

import sys

from bkr.client import BeakerCommand


class Pool_List(BeakerCommand):
    """
    List pools
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option('--owner',
                               metavar='USERNAME',
                               help='List pools owned by USERNAME')
        self.parser.add_option('--owning-group',
                               metavar='GROUP',
                               help='List pools owned by GROUP')
        self.parser.add_option("--limit",
                               default=50,
                               type=int,
                               help='Limit results to this many [default: %default]')

    def run(self, *args, **kwargs):
        owner = kwargs.get('owner', None)
        owning_group = kwargs.get('owning_group', None)
        limit = kwargs.get('limit')

        if len(list(filter(None, [owner, owning_group]))) > 1:
            self.parser.error('Only one of --owner or --owning-group may be specified')

        self.set_hub(**kwargs)

        requests_session = self.requests_session()

        params = {'page_size': limit}
        if owner:
            params['q'] = 'owner.user_name:%s' % owner
        elif owning_group:
            params['q'] = 'owner.group_name:%s' % owning_group

        response = requests_session.get('pools/',
                                        params=params,
                                        headers={'Accept': 'application/json'})
        response.raise_for_status()
        attributes = response.json()
        pools = attributes['entries']

        if not pools:
            sys.stderr.write('Nothing Matches\n')
            sys.exit(1)

        for pool in pools:
            print(pool['name'])
