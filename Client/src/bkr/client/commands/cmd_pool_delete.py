
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-pool-delete:

bkr pool-delete: Delete a system pool
=====================================

.. program:: bkr pool-delete

Synopsis
--------

| :program:`bkr pool-delete` <poolname> ..

Description
-----------

Deletes a Beaker system pool.

.. versionadded:: 20

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Delete an existing system pool called "beakerdevs"::

    bkr pool-delete beakerdevs

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr pool-create`, :manpage:`bkr pool-modify`

"""


from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Pool_Delete(BeakerCommand):
    """
    Deletes a system pool
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <poolname>" % self.normalized_name

    def run(self, *args, **kwargs):

        if not args:
            self.parser.error('One or more system pool names must be specified')
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        for pool in args:
            res = requests_session.delete('pools/%s/' % parse.quote(pool, ''))
            res.raise_for_status()
