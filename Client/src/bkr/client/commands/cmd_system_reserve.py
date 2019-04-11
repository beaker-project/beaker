
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr system-reserve: Manually reserve a Beaker system
====================================================

.. program:: bkr system-reserve

Synopsis
--------

:program:`bkr system-reserve` [*options*] <fqdn>

Description
-----------

Reserves a Beaker system.

The system must have its status set to ``Manual`` and be free for use by the 
current user. To reserve a system using the Beaker scheduler, submit a job 
using the Beaker web UI or a workflow command (such as :program:`bkr 
workflow-simple`) instead.

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

See also
--------

:manpage:`bkr(1)`
"""

from bkr.client import BeakerCommand


class System_Reserve(BeakerCommand):
    """
    Reserve a system for manual usage
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        self.set_hub(**kwargs)
        self.hub.systems.reserve(fqdn)
