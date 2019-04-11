
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr pool-modify: Modify a system pool
=====================================

.. program:: bkr pool-modify

Synopsis
--------

| :program:`bkr pool-modify` [*options*] <poolname>
|       [:option:`--name` <name>]
|       [:option:`--description` <description>]
|       [:option:`--owner` <user> | :option:`--owning-group` <group>]

Description
-----------

Modify the name, description or owner of an existing system pool.

(Note: this command requires Python 2.6 or later)

.. versionadded:: 20

Options
-------

.. option:: --name <name>

   Rename the system pool to <name>

.. option:: --description <description>

   Change the system pool's description to <description>

.. option:: --owner <user>

   Change the system pool's owner to user <user>

.. option:: --owning-group <groupname>

   Change the system pool's owning group to group <groupname>

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Rename the system pool "mypool" to "mynewpool"::

    bkr pool-modify --name mynewpool mypool

Change the owner of "mypool" to user "user"::

    bkr pool-modify --owner user mypool

See also
--------

:manpage:`bkr(1)`
"""

from bkr.client import BeakerCommand


class Pool_Modify(BeakerCommand):
    """
    Modify attributes of an existing system pool
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <poolname>" % self.normalized_name
        self.parser.add_option('--name', metavar='NAME',
            help='Rename the pool to NAME')
        self.parser.add_option('--description', metavar='DESCRIPTION',
            help='Change the description of the pool to DESCRIPTION')
        self.parser.add_option('--owner', metavar='USER',
            help='Change the owner to USER')
        self.parser.add_option('--owning-group', metavar='GROUP',
            help='Change the owner to group GROUP')

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one pool name must be specified.')
        pool_name = args[0]

        new_name = kwargs.get('name', None)
        description = kwargs.get('description', None)
        owner = kwargs.get('owner', None)
        owning_group = kwargs.get('owning_group', None)

        if not any([new_name, description, owner, owning_group]):
            self.parser.error('At least one option is required, specifying what to change')
        if owner and owning_group:
            self.parser.error('Only one of --owner or --owning-group must be specified')

        pool_attr = {}
        if new_name:
            pool_attr['name'] = new_name
        if description:
            pool_attr['description'] = description
        if owner:
            pool_attr['owner'] = {'user_name': owner}
        if owning_group:
            pool_attr['owner'] = {'group_name': owning_group}

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        url = 'pools/%s/' % pool_name
        res = requests_session.patch(url, json=pool_attr)
        res.raise_for_status()
