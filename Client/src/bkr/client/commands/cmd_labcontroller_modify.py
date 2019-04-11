
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-labcontroller-modify:

bkr labcontroller-modify: Modify a lab controller
=====================================================

.. program:: bkr labcontroller-modify

Synopsis
--------

| :program:`bkr labcontroller-modify` [*options*] <fqdn>
|       [:option:`--fqdn` <fqdn>]
|       [:option:`--user` <username>]
|       [:option:`--password` <password>]
|       [:option:`--email` <email_address>]
|       [:option:`--enable`]
|       [:option:`--disable`]

Description
-----------

Modify the attributes of an existing lab controller.

Options
-------

.. option:: --fqdn <fqdn>

   Change the lab controller's FQDN to <fqdn>

.. option:: --user <username>

   Change the username of the lab controller's user account to <username>

.. option:: --password <password>

   Change the password of the lab controller's user account to <password>

.. option:: --email <email_address>

   Change the email address of the lab controller's user account to <email-address>

.. option:: --create

   Create the lab controller if it does not exist

.. option:: --enable

   Enable the lab controller

.. option:: --disable

   Disable the lab controller

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Change the lab controller 'lab1.fqdn.name' with new fqdn 'lab2.fqdn.name'::

    bkr labcontroller-modify --fqdn lab2.fqdn.name lab1.fqdn.name

Change the lab controller 'lab1.fqdn.name' with new user account details::

    bkr labcontroller-modify \
        --user newusername \
        --password newpass \
        --email newemail.example.com \
        lab1.fqdn.name

See also
--------

:manpage:`bkr labcontroller-list(1)`

"""

from six.moves.urllib import parse

from bkr.client import BeakerCommand


class LabController_Modify(BeakerCommand):
    """
    Modify attributes of an existing lab controller
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options> <fqdn> .." % self.normalized_name
        self.parser.add_option('--fqdn', metavar='FQDN',
                               help="Change the lab controller's FQDN to FQDN")
        self.parser.add_option('-u', '--user', action="store", type="string",
                               dest="user_name",
                               help="Change the username of the lab controller's user account to USER")
        self.parser.add_option('-p', '--password', action="store", type="string",
                               dest="password",
                               help="Change the password of the lab controller's user account to PASSWORD")
        self.parser.add_option('-e', '--email', action="store", type="string",
                               dest="email_address",
                               help="Change the email of the lab controller's user account to EMAIL ADDRES")
        self.parser.add_option('--create', action='store_true',
                help='Create the lab controller if it does not exist')
        self.parser.add_option('--enable', action='store_false',
                dest="disabled",
                help='Enable the lab controller')
        self.parser.add_option('--disable', action='store_true',
                dest="disabled",
                help='Disable the lab controller')

    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error('Exactly one lab controller fqdn must be specified.')
        fqdn = args[0]
        lc_data = {}
        for key in ['fqdn', 'user_name', 'password', 'email_address', 'disabled']:
            value = kwargs.pop(key, None)
            if value is not None:
                lc_data[key] = value
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        update = True
        if kwargs.pop('create', False):
            lc_data['fqdn'] = fqdn
            res = requests_session.post('labcontrollers/', json=lc_data)
            # If the lab controller already exists, fall back to send a PATCH request.
            if res.status_code != 409:
                update = False
                res.raise_for_status()
        if update:
            url = 'labcontrollers/%s' % parse.quote(fqdn, '')
            res = requests_session.patch(url, json=lc_data)
            res.raise_for_status()
