
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr remove-account: Remove user accounts
========================================

.. program:: bkr remove-account

Synopsis
--------

| :program:`bkr remove-account` <user>...

Description
-----------

Removes a Beaker user account.

When the account is removed:

* it is removed from all groups and access policies
* any running jobs owned by the account are cancelled
* any systems reserved by or loaned to the account are returned
* any systems owned by the account are transferred to the admin running this 
  command, or some other user if specified using :option:`--new-owner`
* the account is disabled for further login

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Options
-------

.. option:: --new-owner <username>

   Transfers the ownership of any systems currently owned by the closed
   accounts to USERNAME.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Close the accounts of users, user1 and user2::

    bkr remove-account user1 user2

Close the account of user1 and assign their systems to user2::

    bkr remove-account --new-owner=user2 user1

See also
--------

:manpage:`bkr(1)`
"""

from bkr.client import BeakerCommand


class Remove_Account(BeakerCommand):
    """
    Remove user accounts
    """

    enabled=True

    def options(self):
        self.parser.usage = '%%prog %s' % self.normalized_name
        self.parser.add_option(
            '--new-owner',
            metavar='USERNAME',
            help=('Transfer ownership of any systems currently owned by '
                  'the closed accounts to USERNAME [default: '
                  'the admin running this command]')
        )

    def run(self, *args, **kwargs):

        if not args:
            self.parser.error('Please provide the username(s) of the account to remove')

        self.set_hub(**kwargs)
        for username in args:
            self.hub.users.remove_account(username, kwargs.get('new_owner'))
