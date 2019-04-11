
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr group-create: Create a group
================================

.. program:: bkr group-create

Synopsis
--------

| :program:`bkr group-create` [*options*] <group-name>

Description
-----------

Create a new group with the specified name, display name and root password.

Options
-------

.. option:: --ldap

   Populate the members from an LDAP group, specified by <group-name>.

.. option:: --display-name

   Display name of the group.

.. option:: --description

   Description of the group.

.. option:: --root-password

   Root password for group jobs.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Create a group with the following group name, display name, and root password: 'mygroup',
'My Group', and 'd3c0yz3d' respectively::

    bkr group-create --display-name="My Group" --root-password="d3c0yz3d" mygroup

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from bkr.client import BeakerCommand


class Group_Create(BeakerCommand):
    """
    Create a Group
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <group-name>" % self.normalized_name
        self.parser.add_option(
            "--display-name",
            help="Display name of the group",
        )

        self.parser.add_option(
            "--description",
            help="Description of the group",
        )

        self.parser.add_option(
            "--ldap",
            default=False,
            action="store_true",
            help="Create an LDAP group",
        )

        self.parser.add_option(
            "--root-password",
            help="Root password used for group jobs",
        )

    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one group name must be specified.')

        group_name = args[0]
        display_name = kwargs.get('display_name')
        description = kwargs.get('description', None)
        if not display_name:
            display_name = group_name
        ldap = kwargs.get('ldap', False)
        password = kwargs.get('root_password', None)

        self.set_hub(**kwargs)

        request_session = self.requests_session()
        res = request_session.post('groups/', json=dict(group_name=group_name,
                                                        root_password=password,
                                                        display_name=display_name,
                                                        description=description,
                                                        ldap=ldap))
        res.raise_for_status()
        print('Group created: %s.' % group_name)