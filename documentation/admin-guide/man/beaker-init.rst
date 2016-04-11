beaker-init: Initialize and populate the Beaker database
========================================================

.. program:: beaker-init

Synopsis
--------

| :program:`beaker-init` [*options*]

Description
-----------

Initializes and populates Beaker's database if empty, or upgrades it to the 
latest schema version.

This command reads the server configuration and connects to the database in the 
same way as the Beaker application itself does. For new Beaker installations, 
ensure you have configured the database in :file:`/etc/beaker/server.cfg` 
before you run this command so that it can connect to the database in order to 
initialize it.

When initializing an empty database, you must supply the :option:`--user`, 
:option:`--password`, :option:`--email`, and :option:`--fullname` options so 
that :program:`beaker-init` can create an admin account.

This command requires read access to the Beaker server configuration. Run it as 
root.

Options
-------

.. option:: -c <path>, --config <path>

   Read server configuration from <path> instead of the default 
   :file:`/etc/beaker/server.cfg`.

.. option:: --user <username>

   Create a new user with administrative privileges using the given username.

.. option:: --password <password>

   Set the administrative user's password to the given value. This can be used 
   as an escape hatch in case you are unable to log in to Beaker as an admin.

.. option:: --email <email>

   Update the administrative user's email address to the given value.

.. option:: --fullname <name>

   Human-friendly display name for the administrative user.

.. option:: --downgrade <version>

   Downgrade the database to the given version instead of upgrading.
   
   The version may be given as a Beaker version number with any number of 
   components (for example, ``22`` or ``22.0-1.el6eng``), or it may be given as 
   a schema version identifier as listed in :ref:`downgrading` (for example, 
   ``54395adc8646``).

.. option:: --check

   Check if the database schema is up to date, instead of performing any 
   upgrades.

   When this option is given the database is not modified. If the database is 
   up to date (that is, running :program:`beaker-init` would not perform any 
   upgrades) then the exit status will be 0. If the database is not up to date 
   then the exit status will be 1.

   If this option is combined with :option:`--downgrade` then the check will be 
   performed against the requested downgrade version, not the latest version.

.. option:: --background

   Detach from the terminal and send all log messages to syslog. The pid of the 
   background process is written to :file:`/var/run/beaker-init.pid`, and 
   removed when the background process is complete.

.. option:: --debug

   Show detailed progress information and debugging messages.


Exit status
-----------

For normal operations the exit status is zero on success, or non-zero on error. 

When the :option:`--check` option is used, the exit status is zero if the 
database is up to date, 1 if it is requires updates, or some other value on 
error.

Examples
--------

Populate the database for a new Beaker installation::

    beaker-init --user admin \
        --password changeme \
        --email dcallagh@redhat.com \
        --fullname 'Dan Callaghan'

Upgrade an existing Beaker database, while Beaker is offline (see 
:doc:`../upgrading`)::

    beaker-init

If your Beaker site does automated deployments with a tool such as Ansible, you 
can combine the :option:`--background` and :option:`--check` options to perform 
long-running database upgrades in a robust manner. For example, the following 
Ansible tasks invoke :program:`beaker-init` in the background, wait for the pid 
file to be removed, and then check that the background process completed 
successfully::

    - name: start db migration
      command: beaker-init --background --debug
    
    - name: wait for db migration to finish
      wait_for: path=/var/run/beaker-init.pid state=absent
    
    - name: check db migration completed successfully
      command: beaker-init --check
      changed_when: False
