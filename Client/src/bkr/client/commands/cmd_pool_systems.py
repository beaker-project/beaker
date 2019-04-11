
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr pool-systems: List systems in a pool
========================================

.. program:: bkr pool-systems

Synopsis
--------

| :program:`bkr pool-systems` [*options*] <pool-name>

Description
-----------

Lists systems in a pool.

Options
-------

.. option:: --format <format>

    Display results in the given format, either ``list`` or ``json``.
    The default format is ``list``, which lists one system per line. The 
    ``json`` format displays systems as a JSON array.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

List systems in the ``kernel-hw`` pool::

    bkr pool-systems kernel-hw

See also
--------

:manpage:`bkr(1)`

"""

from __future__ import print_function

import json

from bkr.client import BeakerCommand


class Pool_Systems(BeakerCommand):
    """
    List systems in a pool
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <pool-name>" % self.normalized_name
        self.parser.add_option(
            '--format',
            type='choice',
            choices=['list', 'json'],
            default='list',
            help='Results display format: json, list [default: %default]',
        )

    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one pool name must be specified')

        pool_name = args[0]

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        response = requests_session.get('pools/%s' % pool_name,
                                        headers={'Accept': 'application/json'})
        response.raise_for_status()
        attributes = response.json()
        systems = attributes['systems']

        if kwargs['format'] == 'json':
            print(json.dumps(systems))
        else:
            for system in systems:
                print(system)
