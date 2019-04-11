
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-pool-remove:

bkr pool-remove: Remove systems from a pool
===========================================

.. program:: bkr pool-remove

Synopsis
--------

| :program:`bkr pool-remove` [*options*]
|       :option:`--pool` <poolname>
|       :option:`--system` <fqdn>

Description
-----------

Removes systems from a system pool.

(Note: this command requires Python 2.6 or later)

.. versionadded:: 20

Options
-------

.. option:: --pool <poolname>

   The system pool to remove the systems from. This option is mandatory.

.. option:: --system <fqdn>

   Remove the system specified by <fqdn> from the system pool
   <poolname>. This option can be specified multiple times to remove
   more than one system from the pool.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Zero if all systems were removed from the pool successfully. Non-zero if any
system could not be removed from the pool. Note that in this case, some
systems may have been successfully removed before the error occurred.

Examples
--------

Remove the system "fqdn1.example.com" from the "beakerdevs" system pool::

    bkr pool-remove --pool beakerdevs --system fqdn1.example.com

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-pool-add(1)`

"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Pool_Remove(BeakerCommand):
    """
    Removes systems from a system pool
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options> <poolname>" % self.normalized_name
        self.parser.add_option('--pool', metavar='POOL',
                               help='Add systems to pool POOL')
        self.parser.add_option('--system', metavar='FQDN',
                               action='append', default=[],
                               help='Remove the system FQDN from system pool')

    def run(self, *args, **kwargs):

        if args:
            self.parser.error('This command does not accept any positional arguments')
        pool = kwargs.pop('pool', None)
        systems = kwargs.pop('system')
        if not pool:
            self.parser.error('System pool name must be specified using --pool')
        if not systems:
            self.parser.error('No system specified using --system')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        for s in systems:
            res = requests_session.delete('pools/%s/systems/?fqdn=%s' %
                                          (parse.quote(pool), parse.quote(s)))
            res.raise_for_status()
