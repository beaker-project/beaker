# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr user-modify: Modify Beaker users
====================================

.. program:: bkr user-modify

Synopsis
--------

| :program:`bkr user-modify` [*options*] [:option:`--add-submission-delegate` <user>]
|       [:option:`--remove-submission-delegate` <user>]

Description
-----------

Modify a Beaker user.

Allows the adding or removing of submission delegates of the currently
logged in user.

.. _user-modify-options:

Options
-------

.. option:: --add-submission-delegate=<user>

   Adds a new submission delegate

.. option:: --remove-submission-delegate=<user>

    Removes an existing submission delegate

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Add a new submission delegate:

    bkr user-modify --add-submission-delegate=mydelegate

Remove an existing delegate:

    bkr user-modify --remove-submission-delegate=mydelegate

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

from sys import exit

from bkr.client import BeakerCommand


class User_Modify(BeakerCommand):
    """
    Modify certain user properties
    """

    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options]" % self.normalized_name
        self.parser.add_option(
            "-a",
            "--add-submission-delegate",
            help="Add a new submission delegate"
        )

        self.parser.add_option(
            "-r",
            "--remove-submission-delegate",
            help="Remove an existing submission delegate"
        )

    def run(self, *args, **kwargs):
        delegate_to_add = kwargs.get('add_submission_delegate', None)
        delegate_to_remove = kwargs.get('remove_submission_delegate', None)
        self.set_hub(**kwargs)
        if delegate_to_remove:
            self.hub.prefs. \
                remove_submission_delegate_by_name(delegate_to_remove)
            print('Removed submission delegate %s' % delegate_to_remove)
        if delegate_to_add:
            self.hub.prefs. \
                add_submission_delegate_by_name(delegate_to_add)
            print('Added submission delegate %s' % delegate_to_add)
        exit(0)
