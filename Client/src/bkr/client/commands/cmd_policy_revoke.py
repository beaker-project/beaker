# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-policy-revoke:

bkr policy-revoke: Revoke permissions in an access policy
=========================================================

.. program:: bkr policy-revoke

Synopsis
--------

| :program:`bkr policy-revoke` [*options*]
|       [:option:`--system` <fqdn> | :option:`--pool` <name>]
|       :option:`--permission` <permission> [:option:`--permission` <permission> ...]
|       [:option:`--user` <username> | :option:`--group` <groupname> | :option:`--everybody`]

Description
-----------

Modifies the access policy to revoke permissions for the given users or groups.

Options
-------

.. option:: --system <fqdn>

   Modify the custom access policy for <fqdn>. This option is mutuallly
   exclusive with :option:`--pool`.

.. option:: --pool <name>

   Modify the access policy for the named system pool. This option
   is mutually exclusive with :option:`--system`.

.. option:: --permission <permission>

   Revoke <permission>. This option must be specified at least once. For 
   a description of the available permissions, see 
   :ref:`system-access-policies`.

.. option:: --user <username>

   Revoke permissions for <username>. This option may be specified multiple 
   times, and may be used in combination with :option:`--group`.

.. option:: --group <groupname>

   Revoke permissions for <groupname>. This option may be specified multiple 
   times, and may be used in combination with :option:`--user`.

.. option:: --everybody

   Revoke permissions which were granted to all Beaker users. This option is 
   mutually exclusive with :option:`--user` and :option:`--group`.

   Note that this option only revokes an access policy rule which applies to 
   all Beaker users (for example, created using ``bkr policy-grant 
   --everybody``). It *does not* revoke permissions which have been granted to 
   a specific user or group.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Revoke Beaker developers' permission to reserve a system::

    bkr policy-revoke --system=test1.example.com \\
        --permission=reserve --group=beakerdevs

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-policy-grant(1)`
"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Policy_Revoke(BeakerCommand):
    """
    Revoke permissions in an access policy
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options>" % self.normalized_name
        self.parser.add_option('--system', metavar='FQDN',
                               help='Modify custom access policy for FQDN')
        self.parser.add_option('--pool', metavar='NAME',
                               help='Modify access policy for system pool NAME')
        self.parser.add_option('--permission', metavar='PERMISSION',
                               dest='permissions', action='append', default=[],
                               help='Revoke PERMISSION in policy: '
                                    'view, edit_policy, edit_system, loan_any, loan_self, '
                                    'control_system, reserve')
        self.parser.add_option('--user', metavar='USERNAME',
                               dest='users', action='append', default=[],
                               help='Revoke permission for USERNAME')
        self.parser.add_option('--group', metavar='GROUP',
                               dest='groups', action='append', default=[],
                               help='Revoke permission for GROUP')
        self.parser.add_option('--everybody', action='store_true', default=False,
                               help='Revoke permission granted to all Beaker users')

    def run(self, system=None, pool=None, permissions=None, users=None,
            groups=None, everybody=None, *args, **kwargs):
        if args:
            self.parser.error('This command does not accept any arguments')
        if (not system and not pool) or (system and pool):
            self.parser.error('Specify system using --system or system pool using --pool')
        if not permissions:
            self.parser.error('Specify at least one permission to revoke using --permission')
        if not (users or groups or everybody):
            self.parser.error('Specify at least one user or group '
                              'to revoke permissions for, or --everybody')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        if system:
            rules_url = 'systems/%s/access-policy/rules/' % parse.quote(system, '')
        if pool:
            rules_url = 'pools/%s/access-policy/rules/' % parse.quote(pool, '')

        if users:
            res = requests_session.delete(rules_url,
                                          params=[('permission', p) for p in permissions]
                                                 + [('user', u) for u in users])
            res.raise_for_status()
        if groups:
            res = requests_session.delete(rules_url,
                                          params=[('permission', p) for p in permissions]
                                                 + [('group', g) for g in groups])
            res.raise_for_status()
        if everybody:
            res = requests_session.delete(rules_url,
                                          params=[('permission', p) for p in permissions]
                                                 + [('everybody', '1')])
            res.raise_for_status()
