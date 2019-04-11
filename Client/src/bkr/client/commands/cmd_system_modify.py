# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-system-modify:

bkr system-modify: Modify system attributes
===========================================

.. program:: bkr system-modify

Synopsis
--------

:program:`bkr system-modify` [*options*] <fqdn> ..

Description
-----------

Modify attributes of Beaker systems.

.. versionadded:: 0.19

Options
-------

.. option:: --owner <username>

   Change the system owner to <username>.

.. option:: --condition <condition>

   Change the system condition to <condition>. Valid values are *Automated*, 
   *Manual*, *Broken*, and *Removed*.

.. option:: --host-hypervisor <type>

   Change the system's host hypervisor type to <type>.

   For systems which are virtualized, this field indicates which virtualization 
   technology is used by the host. An empty value indicates that the system is 
   bare metal (not a virtual guest).

.. option:: --pool-policy <poolname>

   Change the active access policy to that of the system pool
   <pool>. The system must be in the pool to use its policy. This must
   be specified only once, and is mutually exclusive with
   :option:`--use-custom-policy`.

.. option:: --use-custom-policy

   Change the active access policy to that of the system's custom
   access policy. This must be specified only once, and is mutually
   exclusive with :option:`--pool-policy`.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Modify the owner of a particular system to jdoe:

    bkr system-modify --owner jdoe test.system.fqdn

Change the active access policy of the system to use mypool's policy:

    bkr system-modify --pool-policy mypool test.system.fqdn

See also
--------

:manpage:`bkr(1)`
"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class System_Modify(BeakerCommand):
    """
    Modify Beaker system attributes
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn> .." % self.normalized_name

        self.parser.add_option('--owner', metavar='USERNAME',
                               help='Change owner to USERNAME')
        self.parser.add_option('--condition', type='choice',
                               choices=['Automated', 'Manual', 'Broken', 'Removed'],
                               help='Change condition: Automated, Manual, Broken, Removed')
        self.parser.add_option('--host-hypervisor', metavar='TYPE',
                               help='Change host hypervisor to TYPE')
        self.parser.add_option('--pool-policy', metavar='POOL',
                               help='Change active access policy to the access policy of POOL')
        self.parser.add_option('--use-custom-policy', action='store_true', default=None,
                               help="Change active access policy to the "
                                    "system's custom access policy")

    def run(self, *args, **kwargs):
        owner = kwargs.pop('owner')
        condition = kwargs.pop('condition')
        host_hypervisor = kwargs.pop('host_hypervisor')
        pool = kwargs.get('pool_policy')
        custom_policy = kwargs.get('use_custom_policy')

        self.set_hub(**kwargs)

        if not args:
            self.parser.error('Specify one or more system FQDNs to modify')

        if not any(option is not None for option in
                   [owner, condition, host_hypervisor, pool, custom_policy]):
            self.parser.error('At least one option is required, specifying what to change')
        if pool and custom_policy:
            self.parser.error('Only one of --pool-policy or'
                              ' --use-custom-policy must be specified')
        system_attr = {}
        if owner:
            system_attr['owner'] = {'user_name': owner}
        if condition:
            system_attr['status'] = condition.title()
        if host_hypervisor == '':
            system_attr['hypervisor'] = None
        elif host_hypervisor:
            system_attr['hypervisor'] = host_hypervisor
        if pool:
            system_attr['active_access_policy'] = {'pool_name': pool}
        if custom_policy:
            system_attr['active_access_policy'] = {'custom': True}

        requests_session = self.requests_session()
        for fqdn in args:
            system_update_url = 'systems/%s/' % parse.quote(fqdn, '')
            res = requests_session.patch(system_update_url, json=system_attr)
            res.raise_for_status()
