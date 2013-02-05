
"""
bkr system-release: Release a reserved Beaker system
====================================================

.. program:: bkr system-release

Synopsis
--------

:program:`bkr system-release` [*options*] <fqdn>

Description
-----------

Releases a Beaker system which has been manually reserved (using :program:`bkr 
system-reserve` or the Beaker web UI).

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

class System_Release(BeakerCommand):
    """Release a reserved system"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        self.set_hub(**kwargs)
        self.hub.systems.release(fqdn)
