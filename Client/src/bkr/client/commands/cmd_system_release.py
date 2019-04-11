
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-system-release:

bkr system-release: Release a reserved Beaker system
====================================================

.. program:: bkr system-release

Synopsis
--------

:program:`bkr system-release` [*options*] <fqdn>...

Description
-----------

Releases a Beaker system which has been reserved (using :program:`bkr
system-reserve` or the Beaker web UI or the <reservesys/> in the job XML).

Options
-------

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Reserve a particular system, provision it, do some work on it, and then release 
it::

    bkr system-reserve system1.example.invalid
    bkr system-provision --kernel-opts "nogpt" \\
                         --distro-tree 12345 \\
                         system1.example.invalid
    # do some work on the system
    bkr system-release system1.example.invalid

Release more than one system::

    bkr system-release system1.example.invalid system2.example.invalid

See also
--------

:manpage:`bkr(1)`
"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class System_Release(BeakerCommand):
    """
    Release a reserved system
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>..." % self.normalized_name

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)
        for fqdn in args:
            update_url = 'systems/%s/reservations/+current' % parse.quote(fqdn, '')
            requests_session = self.requests_session()
            res = requests_session.patch(update_url, json={'finish_time': 'now'})
            res.raise_for_status()
