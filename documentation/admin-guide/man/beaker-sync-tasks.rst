.. _beaker-sync-tasks:

beaker-sync-tasks: Tool to sync local Beaker task RPMs from a remote Beaker installation
========================================================================================

.. program:: beaker-sync-tasks

Synopsis
--------

| :program:`beaker-sync-tasks` [*options*]

Description
-----------

``beaker-sync-tasks`` is a script to sync local task RPMs from a remote Beaker installation.

Syncing protocol:

- Task doesn't exist in local: copy it.
- Task exists in local: Overwrite it, if it is a different version
  on the remote
- Tasks which exist on the local and not on the remote are left
  untouched

Options
-------

.. option:: -h, --help

   Show this help message and exit

.. option:: --remote <remote_server>

   Remote Beaker Instance

.. option:: --force

   Do not ask before overwriting task RPMs

.. option:: --debug

   Display messages useful for debugging (verbose)

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Sync tasks from a remote Beaker server and display debug messages:

    beaker-sync-tasks --remote=http://127.0.0.1/bkr --debug

Don't prompt before beginning task upload:

    beaker-sync-tasks --remote=http://127.0.0.1/bkr --force

More information
----------------

Querying the existing tasks: The script communicates with the remote Beaker server via XML-RPC
calls and directly interacts with the local Beaker database.

Adding new tasks: The tasks to be added to the local Beaker database
are first downloaded in the task directory (usually,
/var/www/beaker/rpms). Each of these tasks are then added to the
Beaker database and finally createrepo is run.
