
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

Remove a Beaker user account.

Removing a user account cancels any running job(s), returns all the systems in
use by the user, modifies by default the ownership of the systems owned to the
admin closing the account, and disables the account for further login.


Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

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
    """Remove user accounts"""

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
