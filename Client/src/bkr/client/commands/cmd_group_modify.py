
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr group-modify: Modify a group
================================

.. program:: bkr group-modify

Synopsis
--------

| :program:`bkr group-modify` [*options*] <group-name>

Description
-----------

Modify an existing group.

Options
-------

.. option:: --display-name

   New display name of the group.

.. option:: --group-name

   New name of the group.

.. option:: --description

   New description of the group.

.. option:: --add-member

   Add a user to the group. This option can be specified multiple
   times to add more than one user to the group. Should a specified
   user fail to be added, all subsequent users are ignored.

.. option:: --remove-member

   Remove a user from the group. This option can be specified multiple
   times to remove more than one user from the group. Should a specified
   user fail to be removed, all subsequent users are ignored.

.. option:: --grant-owner

   Grant group owner permissions to an existing group member.

.. option:: --revoke-owner

   Remove group owner permissions from an existing group owner.

.. option:: --root-password

   Root password for group jobs.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Modify an existing group 'mygroup' with the new display name 'A new group'::

    bkr group-modify --display-name="A new group" mygroup

Modify an existing group 'mygroup' with the new display name 'A new group'
and new group name 'mynewgroup'::

    bkr group-modify --display-name="A new group" --group-name="mynewgroup" mygroup

Add a user with username 'user1' to the group 'mygroup'::

    bkr group-modify --add-member user1 mygroup

Remove an existing group member with username 'user1' from the group 'mygroup'::

    bkr group-modify --remove-member user1 mygroup

Add an existing group member with username 'user1' as an owner of group 'mygroup'::

    bkr group-modify --grant-owner user1 mygroup

Revoke group owner rights from an existing group owner of group 'mygroup' with username 'user1'::

    bkr group-modify --revoke-owner user1 mygroup

See also
--------

:manpage:`bkr(1)`

"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Group_Modify(BeakerCommand):
    """
    Modify an existing Group
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <group-name>" % self.normalized_name

        self.parser.add_option(
            "--display-name",
            help="New display name of the group",
            )

        self.parser.add_option(
            "--group-name",
            help="New name of the group",
            )

        self.parser.add_option(
            "--description",
            help="New description of the group",
            )

        self.parser.add_option(
            "--add-member",
            action='append',
            default=[],
            help="Username of the member to be added to the group",
            )

        self.parser.add_option(
            "--remove-member",
            action='append',
            default=[],
            help="Username of the member to be removed from the group",
            )

        self.parser.add_option(
            "--grant-owner",
            action='append',
            default=[],
            help="Username of the member to grant owner rights",
            )

        self.parser.add_option(
            "--revoke-owner",
            action='append',
            default=[],
            help="Username of the member to revoke owner rights",
            )

        self.parser.add_option(
            "--root-password",
            help="Root password used for group jobs",
        )

    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one group name must be specified.')

        group = args[0]

        display_name = kwargs.get('display_name', None)
        group_name = kwargs.get('group_name', None)
        description = kwargs.get('description', None)
        add_member = kwargs.pop('add_member', [])
        remove_member = kwargs.pop('remove_member', [])
        grant_owner = kwargs.get('grant_owner', None)
        revoke_owner = kwargs.get('revoke_owner', None)
        password = kwargs.get('root_password', None)

        if not any([group_name, display_name, description, add_member, grant_owner,
            revoke_owner, password,remove_member]):
            self.parser.error('Please specify an attribute to modify.')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()

        for member in add_member:
            url = 'groups/%s/members/' % parse.quote(group)
            res = requests_session.post(url, json={'user_name': member})
            res.raise_for_status()

        for member in remove_member:
            url = 'groups/%s/members/' % parse.quote(group)
            res = requests_session.delete(url, params={'user_name': member})
            res.raise_for_status()

        if grant_owner:
            for member in grant_owner:
                url = 'groups/%s/owners/' % parse.quote(group)
                res = requests_session.post(url, json={'user_name': member})
                res.raise_for_status()

        if revoke_owner:
            for member in revoke_owner:
                url = 'groups/%s/owners/' % parse.quote(group)
                res = requests_session.delete(url, params={'user_name': member})
                res.raise_for_status()

        group_attrs = {}
        if group_name:
            group_attrs['group_name'] = group_name
        if display_name:
            group_attrs['display_name'] = display_name
        if description:
            group_attrs['description'] = description
        if password:
            group_attrs['root_password'] = password
        if group_attrs:
            res = requests_session.patch('groups/%s' % parse.quote(group), json=group_attrs)
            res.raise_for_status()
