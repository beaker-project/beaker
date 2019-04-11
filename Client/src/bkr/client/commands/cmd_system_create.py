# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-system-create:

bkr system-create: Create a system
==================================

.. program:: bkr system-create

Synopsis
--------

:program:`bkr system-create` [*options*] <fqdn> ..

Description
-----------

Creates a Beaker system. By default the new system is owned by the
user who created it.

Options
-------

.. option:: --lab-controller <fqdn>

   Attaches the lab controller specified by <fqdn> to the system.

.. option:: --arch <arch>

   Architecture supported by the system. This option can be specified
   multiple times to add more than one architecture supported by
   the system.

.. option:: --location <location>

   Physical location of the system.

.. option:: --power-type <power-type>

   Remote power control type. This value must be a valid power type configured
   by the Beaker administrator (or one of the Beaker defaults).

.. option:: --power-address <power-address>

   Address passed to the power control script.

.. option:: --power-user <power-user>

   Username passed to the power control script.

.. option:: --power-password <power-password>

   Password passed to the power control script.

.. option:: --power-id <power-id>

   Unique identifier passed to the power control script. The meaning of the
   power ID depends on which power type is selected. Typically this field
   identifies a particular plug, socket, port, or virtual guest name.

.. option:: --power-quiescent-period <seconds>

   Quiescent period for power control. Beaker will delay at least this
   long between consecutive power commands. 

.. option:: --release-action <release-action>

   Action to take whenever a reservation for this system is returned:
   ``PowerOff``, ``LeaveOn``, ``ReProvision``. 

.. option:: --reprovision-distro-tree <id>

   Distro tree to be installed when the release action is ``ReProvision``.

.. option:: --condition <condition>

   Ccondition of the system. Valid values are *Automated*, *Manual*,
   *Broken*, and *Removed*.

.. option:: --host-hypervisor <type>

   Type of hypervisor which this system is hosted on.

   For systems which are virtualized, this field indicates which virtualization 
   technology is used by the host. An empty value indicates that the system is 
   bare metal (not a virtual guest).

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Create a system called "beakertestsystem"::

    bkr system-create beakertestsystem

See also
--------

:manpage:`bkr(1)`

"""

from bkr.client import BeakerCommand


class System_Create(BeakerCommand):
    """
    Creates a system
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options> <fqdn>" % self.normalized_name
        self.parser.add_option('--lab-controller', metavar='FQDN',
                               help='Attach the lab controller FQDN to the system')
        self.parser.add_option(
            "--arch",
            action='append',
            default=[],
            help="Architecture supported by the system",
        )
        self.parser.add_option('--location',
                               help='Physical location of the system')
        self.parser.add_option('--power-type', metavar='TYPE',
                               help='Remote power control type')
        self.parser.add_option('--power-address', metavar='ADDRESS',
                               help='Address passed to the power control script')
        self.parser.add_option('--power-user', metavar='USERNAME',
                               help='Username passed to the power control script')
        self.parser.add_option('--power-password', metavar='PASSWORD',
                               help='Password passed to the power control script')
        self.parser.add_option('--power-id',
                               help='Unique identifier passed to the power control script')
        self.parser.add_option('--power-quiescent-period', metavar='SECONDS',
                               help='Quiescent period for power control')
        self.parser.add_option('--release-action', type='choice',
                               choices=['PowerOff', 'LeaveOn', 'ReProvision'],
                               help='Action to take whenever a reservation for this system is '
                                    'returned')
        self.parser.add_option('--reprovision-distro-tree', metavar='ID',
                               help='Distro tree to be installed when the release action is '
                                    'ReProvision')
        self.parser.add_option('--condition', type='choice',
                               choices=['Automated', 'Manual', 'Broken', 'Removed'],
                               help='System Condition: Automated, Manual, Broken, Removed')
        self.parser.add_option('--host-hypervisor', metavar='TYPE',
                               dest='hypervisor',
                               help='Type of hypervisor which this system is hosted on')

    def run(self, *args, **kwargs):

        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        system_attrs = {'fqdn': args[0]}
        attrs = ['location', 'power_type', 'power_address', 'power_user',
                 'power_password', 'power_id', 'power_quiescent_period',
                 'release_action', 'hypervisor']
        for attr in attrs:
            value = kwargs.pop(attr, None)
            if value:
                system_attrs[attr] = value
        lc_fqdn = kwargs.pop('lab_controller', None)
        if lc_fqdn:
            system_attrs['lab_controller'] = {'fqdn': lc_fqdn}
        arches = kwargs.pop('arch', [])
        if arches:
            system_attrs['arches'] = arches
        reprovision_distro_tree = kwargs.pop('reprovision_distro_tree', None)
        if reprovision_distro_tree:
            system_attrs['reprovision_distro_tree'] = {'id': reprovision_distro_tree}
        condition = kwargs.pop('condition', None)
        if condition:
            system_attrs['status'] = condition.title()
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        res = requests_session.post('systems/', json=system_attrs)
        res.raise_for_status()
