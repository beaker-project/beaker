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

    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one group name must be specified.')

        group = args[0]
        display_name = kwargs.get('display_name', None)
        group_name = kwargs.get('group_name', None)

        if not (display_name or group_name):
            self.parser.error('Please specify an attribute to modify.')

        self.set_hub(**kwargs)
        self.hub.groups.modify(group, dict(group_name=group_name,
                                           display_name=display_name))
