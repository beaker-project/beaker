# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr whoami: Show your Beaker username
=====================================

.. program:: bkr whoami

Synopsis
--------

:program:`bkr whoami` [*options*]

Description
-----------

Prints to stdout a dict with username and proxied_by_username if proxy
permissions are granted to this user.

Options
-------

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import json

from bkr.client import BeakerCommand


class WhoAmI(BeakerCommand):
    """Who Am I"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        response = requests_session.get('users/+self', headers={'Accept': 'application/json'})
        response.raise_for_status()
        attributes = response.json()
        # Make the output match what came out of the old auth.who_am_i XMLRPC method
        result = {
            'username': attributes['user_name'],
            'email_address': attributes['email_address'],
        }
        if attributes.get('proxied_by_user'):
            result['proxied_by_username'] = attributes['proxied_by_user']['user_name']
        print(json.dumps(result))
