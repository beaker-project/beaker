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

   New name of the group

.. option:: --add-member

   Add a user to the group

.. option:: --remove-member

   Remove a user from the group

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

See also
--------

:manpage:`bkr(1)`

"""

from bkr.client import BeakerCommand

class Group_Modify(BeakerCommand):
    """Modify an existing Group"""
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
            "--add-member",
            help="Username of the member to add",
            )

        self.parser.add_option(
            "--remove-member",
            help="Username of the member to remove",
            )


    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one group name must be specified.')

        group = args[0]

        display_name = kwargs.get('display_name', None)
        group_name = kwargs.get('group_name', None)
        add_member = kwargs.get('add_member', None)
        remove_member = kwargs.get('remove_member', None)

        attribs = dict(group_name=group_name,
                       display_name=display_name,
                       add_member=add_member,
                       remove_member=remove_member)

        if not any(attribs.values()):
            self.parser.error('Please specify an attribute to modify.')

        self.set_hub(**kwargs)
        self.hub.groups.modify(group, attribs)
