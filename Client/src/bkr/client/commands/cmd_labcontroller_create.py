
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
.. _bkr-labcontroller-create:

bkr labcontroller-create: Create a new lab controller
=====================================================

.. program:: bkr labcontroller-create

Synopsis
--------

| :program:`bkr labcontroller-create` [*options*]
|       :option:`--fqdn` <fqdn>
|       :option:`--user` <username>
|       [:option:`--password` <password>]
|       :option:`--email` <email_address>

Description
-----------

Creates a new Lab controller. 

Options
-------

.. option:: --fqdn <fqdn>

   Set the lab controller's FQDN.

.. option:: --user <username>

   Sets the username for the lab controller's user account. The lab controller
   must be configured to authenticate as this username.

.. option:: --password <password>

   Sets the password for the lab controller's user account, if using password-based
   authentication. The lab controller must be configured to use this password for
   authentication. If your Beaker site is using Kerberos authentication, omit this
   option.

.. option:: --email <email_address>

   Sets the email address for the lab controller's user account.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Create a Lab controller lab1.fqdn.name::

    bkr labcontroller-create \
        --fqdn lab1.fqdn.name \
        --user host/lab1.fqdn.name \
        --password lc1 \
        --email user@lab1.fqdn.name

See also
--------

:manpage:`bkr labcontroller-list(1)`

"""


from bkr.client import BeakerCommand

class LabController_Create(BeakerCommand):
    """
    Creates a new Lab controller
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s <options>" % self.normalized_name
        self.parser.add_option('--fqdn', metavar='FQDN',
                               help="Set the lab controllers's fully-qualified domain name to FQDN")
        self.parser.add_option('-u', '--user', action="store", type="string",
                               dest="user_name",
                               help="Set the username for the lab controller's user account to USER")
        self.parser.add_option('-p', '--password', action="store", type="string",
                               dest="password",
                               help="Set the password for the lab controller's user account to PASSWORD")
        self.parser.add_option('-e', '--email', action="store", type="string",
                               dest="email_address",
                               help="Set the email for the lab controller's user account to EMAIL ADDRES")

    def run(self, *args, **kwargs):
        fqdn = kwargs.pop('fqdn', None)
        user_name = kwargs.pop('user_name', None)
        password = kwargs.pop('password', None)
        email_address = kwargs.pop('email_address', None)
        if not fqdn:
            self.parser.error('The --fqdn option must be specified')
        if not user_name:
            self.parser.error('The --user option must be specified')
        lc_data = {'fqdn': fqdn,
                   'user_name': user_name,
                   'password': password,
                   'email_address': email_address
                   }
        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        res = requests_session.post('labcontrollers/', json=lc_data)
        res.raise_for_status()
