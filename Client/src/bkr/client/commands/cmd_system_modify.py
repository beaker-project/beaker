
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

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Modify the owner of a particular system to jdoe:

    bkr system-modify --owner jdoe test.system.fqdn

See also
--------

:manpage:`bkr(1)`
"""

import urllib
from bkr.client import BeakerCommand

class System_Modify(BeakerCommand):
    """Modify Beaker system attributes"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn> .." % self.normalized_name

        self.parser.add_option('--owner', metavar='USERNAME',
                help='Change owner to USERNAME')
        self.parser.add_option('--condition', type='choice',
                choices=['Automated', 'Manual', 'Broken', 'Removed'],
                help='Change condition: Automated, Manual, Broken, Removed')

    def run(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        condition = kwargs.pop('condition', None)

        self.set_hub(**kwargs)

        json_data = {}
        if owner:
            json_data['owner'] = {'user_name': owner}
        if condition:
            json_data['status'] = condition.title()
        if not json_data:
            self.parser.error('At least one option is required, specifying what to change')

        for fqdn in args:
            system_update_url = 'systems/%s/' % urllib.quote(fqdn, '')
            requests_session = self.requests_session()
            res = requests_session.patch(system_update_url, json=json_data)
            res.raise_for_status()
