
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-loan-grant:

bkr loan-grant: Grant a loan for a Beaker system
================================================

.. program:: bkr loan-grant

Synopsis
--------

:program:`bkr loan-grant` [*options*] <fqdn>

Description
-----------

Grant a loan for a Beaker system.

The designated user will have full permissions to reserve, provision and
schedule jobs on that system, even if they would not normally have such
access.

While a system is on loan, only the loan recipient and the system owner
will have permission to reserve or otherwise use the system.

.. versionadded:: 0.15.2

Options
-------

.. option:: --recipient

   Username of the loan recipient (defaults to the user issuing the command)

.. option:: --comment

   Comment regarding the loan (for example, the reason for it)


Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Temporarily grant a user exclusive access to a particular system::

    bkr loan-grant --recipient jdoe system1.example.invalid
    # jdoe now has almost exclusive access to use the system
    bkr loan-return system1.example.invalid
    # Either jdoe or a user with permission to loan the system to other users
    # can return the granted loan

See also
--------

:manpage:`bkr(1)`
"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Loan_Grant(BeakerCommand):
    """
    Loan a system to a specific user
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name

        self.parser.add_option(
            "--recipient",
            help="Username of the loan recipient",
            )

        self.parser.add_option(
            "--comment",
            help="Comment regarding the loan",
            )

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')

        fqdn = args[0]
        recipient = kwargs.pop('recipient', None)
        comment = kwargs.pop('comment', None)

        self.set_hub(**kwargs)
        grant_url = 'systems/%s/loans/' % parse.quote(fqdn, '')
        data = {'recipient': recipient, 'comment': comment}
        requests_session = self.requests_session()
        res = requests_session.post(grant_url, json=data)
        res.raise_for_status()
