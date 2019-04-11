# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr system-provision: Provision a Beaker system
===============================================

.. program:: bkr system-provision

Synopsis
--------

| :program:`bkr system-provision` [*options*]
|       [:option:`--ks-meta` <variables>]
|       [:option:`--kernel-options` <opts>]
|       [:option:`--kernel-options-post` <opts>]
|       [:option:`--kickstart` <file>]
|       [--no-reboot]
|       :option:`--distro-tree` <id>
|       <fqdn>

Description
-----------

Provisions the given system with the given distro. Pass extra options to 
customise the OS installation.

The system must have its status set to ``Manual`` and be already reserved by 
the current user. To provision a system using the Beaker scheduler, submit 
a job using the Beaker web UI or a workflow command (such as :program:`bkr 
workflow-simple`) instead.

Options
-------

.. option:: --distro-tree <id>

   Provision the distro tree identified by <id>.

   The distro tree id can be found in Beaker's web UI or by using 
   :program:`bkr distro-trees-list`.

.. option:: --ks-meta <variables>

   Pass additional kickstart metadata <variables> to Cobbler. The variables 
   string is applied on top of any variables which are set by default for the 
   chosen system and distro.

.. option:: --kernel-options <opts>

   Pass additional kernel options for during installation. The options string 
   is applied on top of any install-time kernel options which are set by 
   default for the chosen system and distro.

.. option:: --kernel-options-post <opts>

   Pass additional kernel options for after installation. The options string is 
   applied on top of any post-install kernel options which are set by default 
   for the chosen system and distro.

.. option:: --kickstart <file>

   Pass <file> as the kickstart for installation. If <file> is '-', the 
   kickstart is read from stdin.

   The kickstart must be a complete kickstart (not just a snippet). Beaker will 
   not make any of the usual Beaker-related customisations to the kickstart; 
   only the install location for the selected distro will be prepended to the 
   top of the kickstart.

.. option:: --no-reboot

   Performs all the necessary steps to set up the system to be provisioned with 
   the selected distro, but skips the final step of booting the system into the 
   installation environment.

   If :option:`--no-reboot` is passed, this command will have no effect unless 
   a system is subsequently rebooted by using :program:`bkr system-power` (or 
   by some other means).

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

History
-------

Prior to version 0.9.1, this command accepted --distro instead of :option:`--distro-tree`.

See also
--------

:manpage:`bkr-workflow-simple(1)`, :manpage:`bkr-system-power(1)`, :manpage:`bkr(1)`
"""

import optparse
import sys

from bkr.client import BeakerCommand


class System_Provision(BeakerCommand):
    """
    Provision a system with a distro
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name
        self.parser.add_option('--distro-tree', metavar='ID',
                               help='Provision distro tree identified by ID')
        self.parser.add_option('--distro', help=optparse.SUPPRESS_HELP)
        self.parser.add_option('--ks-meta', metavar='OPTS',
                               help='Pass OPTS as kickstart metadata')
        self.parser.add_option('--kernel-options', metavar='OPTS',
                               help='Pass OPTS as kernel options during installation')
        self.parser.add_option('--kernel-options-post', metavar='OPTS',
                               help='Pass OPTS as kernel options after installation')
        self.parser.add_option('--kickstart', metavar='FILENAME',
                               help='Read complete kickstart from FILENAME (- for stdin)')
        self.parser.add_option('--no-reboot',
                               action='store_false', dest='reboot',
                               help="Configure installation but don't reboot system")
        self.parser.set_defaults(reboot=True)

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        # Accept --distro for backwards compat
        if kwargs['distro'] and not kwargs['distro_tree']:
            kwargs['distro_tree'] = kwargs['distro']

        if not kwargs['distro_tree']:
            self.parser.error('Distro tree must be specified with --distro-tree')

        if kwargs['kickstart'] == '-':
            kickstart = sys.stdin.read()
        elif kwargs['kickstart']:
            kickstart = open(kwargs['kickstart'], 'r').read()
        else:
            kickstart = None

        self.set_hub(**kwargs)
        self.hub.systems.provision(fqdn, kwargs['distro_tree'],
                                   kwargs['ks_meta'], kwargs['kernel_options'],
                                   kwargs['kernel_options_post'], kickstart, kwargs['reboot'])
