# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-policy-grant:

bkr policy-grant: Grant permissions in an access policy
=======================================================

.. program:: bkr policy-grant

Synopsis
--------

| :program:`bkr policy-grant` [*options*]
|       [:option:`--system` <fqdn> | :option:`--pool` <name>]
|       :option:`--permission` <permission> [:option:`--permission` <permission> ...]
|       [:option:`--user` <username> | :option:`--group` <groupname> | :option:`--everybody`]

Description
-----------

Modifies the access policy to grant new permissions to the given users or groups.

(Note: this command requires Python 2.6 or later)

Options
-------

.. option:: --system <fqdn>

   Modify the custom access policy for <fqdn>. This option is mutuallly
   exclusive with :option:`--pool`.

.. option:: --pool <name>

   Modify the access policy for the named system pool. This option
   is mutually exclusive with :option:`--system`.

.. option:: --permission <permission>

   Grant <permission>. This option must be specified at least once. For 
   a description of the available permissions, see 
   :ref:`system-access-policies`.

.. option:: --user <username>

   Grant permissions to <username>. This option may be specified multiple times, 
   and may be used in combination with :option:`--group`.

.. option:: --group <groupname>

   Grant permissions to <groupname>. This option may be specified multiple times, 
   and may be used in combination with :option:`--user`.

.. option:: --everybody

   Grant permissions to all Beaker users. This option is mutually exclusive 
   with :option:`--user` and :option:`--group`.

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Grant Beaker developers permission to reserve a system::

    bkr policy-grant --system=test1.example.com \\
        --permission=reserve --group=beakerdevs

See also
--------

:manpage:`bkr(1)`, :manpage:`bkr-policy-revoke(1)`
"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class Policy_Grant(BeakerCommand):
    """
    Grant permissions in an access policy
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
                               help='Grant PERMISSION in policy: '
                                    'view, edit_policy, edit_system, loan_any, loan_self, '
                                    'control_system, reserve')
        self.parser.add_option('--user', metavar='USERNAME',
                               dest='users', action='append', default=[],
                               help='Grant permission to USERNAME')
        self.parser.add_option('--group', metavar='GROUP',
                               dest='groups', action='append', default=[],
                               help='Grant permission to GROUP')
        self.parser.add_option('--everybody', action='store_true', default=False,
                               help='Grant permission to all Beaker users')

    def run(self, system=None, pool=None, permissions=None, users=None,
            groups=None, everybody=None, *args, **kwargs):
        if args:
            self.parser.error('This command does not accept any arguments')
        if (not system and not pool) or (system and pool):
            self.parser.error('Specify system using --system or system pool using --pool')
        if not permissions:
            self.parser.error('Specify at least one permission to grant using --permission')
        if not (users or groups or everybody):
            self.parser.error('Specify at least one user or group '
                              'to grant permissions to, or --everybody')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()

        if system:
            rules_url = 'systems/%s/access-policy/rules/' % parse.quote(system, '')
        if pool:
            rules_url = 'pools/%s/access-policy/rules/' % parse.quote(pool, '')
        for permission in permissions:
            for user in users:
                res = requests_session.post(rules_url,
                                            json=dict(permission=permission, user=user,
                                                      group=None, everybody=False))
                res.raise_for_status()
            for group in groups:
                res = requests_session.post(rules_url,
                                            json=dict(permission=permission, group=group,
                                                      user=None, everybody=False))
                res.raise_for_status()
            if everybody:
                res = requests_session.post(rules_url,
                                            json=dict(permission=permission, user=None, group=None,
                                                      everybody=True))
                res.raise_for_status()
