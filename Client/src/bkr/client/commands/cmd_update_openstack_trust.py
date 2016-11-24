# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-update-openstack-trust:

bkr update-openstack-trust: Update OpenStack Keystone trust
===========================================================

.. program:: bkr update-openstack-trust

Synopsis
--------

| :program:`bkr update-openstack-trust`
|       :option:`--os-username` <username>
|       :option:`--os-password` <password>
|       :option:`--os-project-name` <project-name>

Description
-----------

Creates a new OpenStack Keystone trust, which allows Beaker to dynamically
provision OpenStack instances to run your recipes. Any existing Keystone
trust for your account is replaced by the new trust.

This command can only be used when the Beaker administrator has configured
OpenStack integration (see :ref:`openstack`).

Options
-------

.. option:: --os-username <username>, --os-password <password>, --os-project-name <project-name>

   OpenStack credentials for establishing a new trust between Beaker and the given user.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Add a new OpenStack trust to your user::

    bkr update-openstack-trust --os-username=user1 --os-password='supersecret' \\
        --os-project-name=test-project

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client import BeakerCommand


class Update_Openstack_Trust(BeakerCommand):
    """Update OpenStack Keystone trust preferences"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] ..." % self.normalized_name
        self.parser.add_option('--os-username',
                               action='store',
                               type='string',
                               help='OpenStack username')
        self.parser.add_option('--os-password',
                               action='store',
                               type='string',
                               help='OpenStack password')
        self.parser.add_option('--os-project-name',
                               action='store',
                               type='string',
                               help='OpenStack project name')

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        data = {'openstack_username': kwargs.get('os_username'),
                'openstack_password': kwargs.get('os_password'),
                'openstack_project_name': kwargs.get('os_project_name'),
                }
        if not all(data.values()):
            self.parser.error('All options are required: --os-username, --os-password and --os-project-name')

        res = requests_session.put('users/+self/keystone-trust', json=data)
        res.raise_for_status()
