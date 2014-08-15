
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr system-modify: Modify system attributes
===========================================

.. program:: bkr system-modify

Synopsis
--------

:program:`bkr system-modify` [*options*] <fqdn> ..

Description
-----------

Modify a Beaker system attribute.

.. versionadded:: 0.19

Options
-------

.. option:: --owner <username>

   Change the system owner to <username>.


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

        self.parser.add_option(
            "--owner",
            help="Username of the new system owner",
            )

    def run(self, *args, **kwargs):

        owner = kwargs.pop('owner', None)
        self.set_hub(**kwargs)
        json_data = {'owner': {'user_name':owner}}

        for fqdn in args:
            system_update_url = 'systems/%s/' % urllib.quote(fqdn, '')
            requests_session = self.requests_session()
            res = requests_session.patch(system_update_url, json=json_data)
            res.raise_for_status()
