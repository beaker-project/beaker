User preferences
----------------

The preferences page allows the user to configure their email address,
notifications, user interface, submission delegates, SSH public keys,
root password for provisioned systems and OpenStack keystone trust for
running recipes on OpenStack.

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

.. _submission-delegates:


Submission delegates are other users that are given the ability to submit and
manage jobs on behalf of the user. This is intended primarily to grant
automated tools the ability to submit and manage jobs on behalf of users,
without needing access to those users' credentials, and without granting them
the ability to perform other activities as that user (like managing systems
or user groups).

.. _openstack-keystone-trust:


If you want to use OpenStack instances to run your recipes, you must create a Keystone
trust to delegate your roles to Beaker's OpenStack account. Beaker will then use
this trust to create OpenStack instances on your behalf.
