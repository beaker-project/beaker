.. _beaker-log-delete:

beaker-log-delete: Delete expired jobs
======================================

.. program:: beaker-log-delete

Synopsis
--------

| :program:`beaker-log-delete` [*options*]

Description
-----------

Deletes expired jobs and permanently purges log files from Beaker and/or archive server.

This command reads the server configuration and connects to the database in the same way
as the Beaker application itself does. Ensure you have configured the database
in :file:`/etc/beaker/server.cfg` before you run this command so that it can connect to
the database in order to find expired jobs and remove them.

HTTP server must be able to handle WebDAV DELETE operations on the log directory’s base
path (HTTP digest and Kerberos authentication are supported).

To enable HTTP digest, configure account in :file:`/etc/beaker/server.cfg`::

    beaker.log_delete_user = ""
    beaker.log_delete_password = ""

This command requires read access to the Beaker server configuration. Run it as root.

Options
-------

.. option:: -c <path>, --config <path>

    Read server configuration from <path> instead of the default /etc/beaker/server.cfg.

.. option:: -v, --verbose

    Print the path/URL of deleted files to stdout

.. option:: --debug

    Show detailed progress information and debugging messages.

.. option:: --dry-run

    Expired jobs are not removed.

.. option:: --limit

    Limit number of expired jobs whose logs will be deleted.

Exit status
-----------

For normal operations the exit status is zero on success, or non-zero on error.

Examples
--------

Delete first 50 expired jobs::

    beaker-log-delete --limit 50

Delete expired jobs and display debug messages::

    beaker-log-delete --debug

Expired jobs are only listed and not deleted::

    beaker-log-delete --dry-run --verbose

