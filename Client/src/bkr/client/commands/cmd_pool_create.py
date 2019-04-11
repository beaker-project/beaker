
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-pool-create:

bkr pool-create: Create a system pool
=====================================

.. program:: bkr pool-create

Synopsis
--------

| :program:`bkr pool-create` [*options*] <poolname>
|       [:option:`--description` <description>]
|       [:option:`--owning-group` <groupname> | :option:`--owner` <user>]

Description
-----------

Creates a Beaker system pool. By default the new pool is owned by the
user who created it. To set a different owner, use the
:option:`--owning-group` or :option:`--owner` options.

(Note: this command requires Python 2.6 or later)

.. versionadded:: 20

Options
-------

.. option:: --description <description>

   Set the system pool's description

.. option:: --owning-group <groupname>

   Set the owner of the system pool to group <groupname>

.. option:: --owner <user>

   Set the owner of the system pool to user instead of the currently
   logged in user.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Create a system pool called "beakerdevs"::

    bkr pool-create beakerdevs --description "Beaker developers"

Create a system pool called "beakerdevs" with the owner set to group
"beakerdevs"::

    bkr pool-create beakerdevs --owning-group beakerdevs

See also
--------

:manpage:`bkr(1)`

"""


from bkr.client import BeakerCommand


class Pool_Create(BeakerCommand):
    """
    Creates a system pool
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options> <poolname>" % self.normalized_name
        self.parser.add_option('--description', metavar='DESCRIPTION',
                               help='Set the system pool description to DESCRIPTION')
        self.parser.add_option('--owner', metavar='USER',
                               help='Set the system pool owner to USER')
        self.parser.add_option('--owning-group', metavar='GROUP',
                               help='Set the system pool owner to group GROUP')

    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one system pool must be given')
        pool = args[0]
        description = kwargs.pop('description', None)
        pool_data = {
            'name' : pool,
            'description': description
        }
        owner = kwargs.pop('owner', None)
        owning_group = kwargs.pop('owning_group', None)
        if owner and owning_group:
            self.parser.error('Only one of owner or owning-group must be specified')
        if owner:
            pool_data['owner'] = {'user_name': owner}
        if owning_group:
            pool_data['owner'] = {'group_name': owning_group}

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        res = requests_session.post('pools/', json=pool_data)
        res.raise_for_status()
