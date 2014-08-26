beaker-repo-update: Update cached harness packages
==================================================

.. program:: beaker-repo-update

Synopsis
--------

| :program:`beaker-repo-update` [*options*]

Description
-----------

Updates the Beaker server's local cache of harness packages.

The harness and its dependencies are installed on a test system when Beaker is 
running a scheduled job on it.

The harness packages are generally built separately for every distro family 
supported by Beaker (Fedora 20, Red Hat Enterprise Linux 7, etc). The 
:program:`beaker-repo-update` command fetches harness packages for every distro 
family which exists in Beaker. Therefore, the first time you import a new 
distro family into Beaker, you should run :program:`beaker-repo-update` in 
order to cache the harness packages for the new distro family.

This command requires read access to the Beaker server configuration, and write 
access to the harness package cache. Run it as root.

Options
-------

.. option:: -b <url>, --baseurl <url>

   Fetch harness packages from subdirectories under <url>. By default, packages 
   are fetched from the Beaker web site.

.. option:: -d <path>, --basepath <path>

   Cache harness packages in subdirectories under <path>. By default, packages 
   are cached in :file:`/var/www/beaker/harness`. This location is served by 
   Apache, and used by Beaker to install the harness on test systems.

.. option:: --debug

   Show detailed progress information and debugging messages.

.. option:: -c <path>, --config-file <path>

   Read server configuration from <path> instead of the default 
   :file:`/etc/beaker/server.cfg`.

Exit status
-----------

Non-zero on error, otherwise zero.

If fetching packages fails for a particular distro family, a warning is printed 
to stderr and the repo is skipped. This is not considered an error.

Examples
--------

Update the cached harness packages after new versions have been released::

    beaker-repo-update

Fetch release candidate packages from the ``harness-testing`` repositories on 
the Beaker web site::

    beaker-repo-update -b https://beaker-project.org/yum/harness-testing/
