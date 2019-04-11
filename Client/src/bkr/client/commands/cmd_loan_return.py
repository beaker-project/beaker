
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-loan-return:

bkr loan-return: Return a current Beaker system loan
====================================================

.. program:: bkr loan-return

Synopsis
--------

:program:`bkr loan-return` [*options*] <fqdn>

Description
-----------

Returns a Beaker system loan that was previously granted using :program:`bkr
loan-grant` or the Beaker web UI).

.. versionadded:: 0.15.2

Options
-------

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


class Loan_Return(BeakerCommand):
    """
    Return a previously granted loan
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        self.set_hub(**kwargs)
        update_url = 'systems/%s/loans/+current' % parse.quote(fqdn, '')
        requests_session = self.requests_session()
        res = requests_session.patch(update_url, json={'finish': 'now'})
        res.raise_for_status()
