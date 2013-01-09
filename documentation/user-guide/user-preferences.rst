User Preferences
----------------

The preferences page allows the user to configure their email address,
SSH public keys and root password for provisioned systems.

Either a hashed password (in crypt format) or a cleartext password may
be entered as a root password. If a plaintext password is entered, it
will first be hashed before being stored. This password will be used as
the root password on systems provisioned by the user.

If Beaker is configured to limit the validity of users' root passwords,
the expiry date and time for your password will be shown here. After
that time, you will be required to change or clear it in order to submit
jobs or provision systems.

If no password is entered, the Beaker default root password will be used
instead.

SSH public keys (e.g. the contents of ``~/.ssh/id_rsa.pub``) may be
added to a users account. These will be added to the ``authorized_keys``
file for the root user on provisioned hosts.
