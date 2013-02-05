bkr: Beaker client
==================

.. program:: bkr

Synopsis
--------

:program:`bkr` <subcommand> [*options*] ...

Description
-----------

Provides a scriptable command-line interface to the Beaker server.

The following subcommands are supported. Each subcommand is documented in its 
own man page. This man page is reserved for common options and features.

* :manpage:`bkr-distro-trees-list(1)` -- List Beaker distro trees
* :manpage:`bkr-distro-trees-verify(1)` -- Check Beaker distro trees for problems
* :manpage:`bkr-distros-edit-version(1)` -- Edit the version of Beaker distros
* :manpage:`bkr-distros-list(1)` -- List Beaker distros
* :manpage:`bkr-distros-tag(1)` -- Tag Beaker distros
* :manpage:`bkr-distros-untag(1)` -- Untag Beaker distros
* :manpage:`bkr-harness-test(1)` -- Generate Beaker job to test harness installation
* :manpage:`bkr-job-cancel(1)` -- Cancel running Beaker jobs
* :manpage:`bkr-job-clone(1)` -- Clone existing Beaker jobs
* :manpage:`bkr-job-delete(1)` -- Delete Beaker jobs
* :manpage:`bkr-job-list(1)` -- List Beaker jobs
* :manpage:`bkr-job-logs(1)` -- Print URLs of Beaker recipe log files
* :manpage:`bkr-job-modify(1)` -- Modify Beaker jobs
* :manpage:`bkr-job-results(1)` -- Export Beaker job results as XML
* :manpage:`bkr-job-submit(1)` -- Submit job XML to Beaker
* :manpage:`bkr-job-watch(1)` -- Watch the progress of a Beaker job
* :manpage:`bkr-list-labcontrollers(1)` -- List Beaker lab controllers
* :manpage:`bkr-list-systems(1)` -- List Beaker systems
* :manpage:`bkr-machine-test(1)` -- Generate Beaker job to test a system
* :manpage:`bkr-system-details(1)` -- Export RDF/XML description of a Beaker system
* :manpage:`bkr-system-power(1)` -- Control power for a Beaker system
* :manpage:`bkr-system-provision(1)` -- Provision a Beaker system
* :manpage:`bkr-system-release(1)` -- Release a reserved Beaker system
* :manpage:`bkr-system-reserve(1)` -- Manually reserve a Beaker system
* :manpage:`bkr-system-delete(1)` -- Delete a Beaker system permanently
* :manpage:`bkr-task-add(1)` -- Upload tasks to Beaker's task library
* :manpage:`bkr-task-details(1)` -- Export details of a Beaker task
* :manpage:`bkr-task-list(1)` -- List tasks in Beaker's task library
* :manpage:`bkr-watchdog-extend(1)` -- Extend Beaker watchdog time
* :manpage:`bkr-watchdog-show(1)` -- Show time remaining on Beaker watchdogs
* :manpage:`bkr-watchdogs-extend(1)` -- Extend Beaker watchdogs time
* :manpage:`bkr-whoami(1)` -- Show your Beaker username
* :manpage:`bkr-workflow-simple(1)` -- Simple workflow to generate Beaker jobs
* :manpage:`bkr-workflow-xslt(1)` -- XSLT-based Beaker job generator

.. _taskspec:

Specifying tasks
****************

Some :program:`bkr` subcommands accept one or more <taskspec> arguments. 
This allows the user to identify a job, or any subcomponent of a job, by its 
id. The format is <type>:<id> where <type> is one of the following 
abbreviations, in descending hierarchical order:

    J
        job
    RS
        recipe set
    R
        recipe
    T
        recipe-task

For example, J:123 might contain RS:456, which might contain R:789, which might 
contain T:1234 and T:5678.

This format is also used in the Beaker web UI to identify jobs and their 
subcomponents.

Options
-------

.. _common-options:

Common options
**************

These options are applicable to all :program:`bkr` subcommands.

.. option:: --hub <url>

   Connect to the Beaker server at the given URL. This overrides the 
   ``HUB_URL`` setting from the configuration file. The URL should not include 
   a trailing slash.

.. option:: --username <username>

   Authenticate using password authentication, with <username>. If a password 
   is not given using :option:`--password`, the user is prompted for the 
   password on stdin.

   This option overrides the authentication type specified in the configuration 
   file, forcing password authentication to be used.

.. option:: --password <password>

   Authenticate using <password>. This option is only applicable when 
   :option:`--username` is also passed.

.. _workflow-options:

Workflow options
****************

These options are applicable to :program:`bkr` workflow subcommands, such as 
:program:`bkr workflow-simple`.

.. option:: --debug

   Print the generated job XML before submitting it to Beaker.

.. option:: --prettyxml

   Pretty-print the generated job XML in a human-readable form (with 
   indentation and line breaks).

.. option:: --dryrun

   Don't submit the job(s) to Beaker.

.. option:: --wait

   Watch the newly submitted job(s) for state changes and print them to stdout. 
   The command will not exit until all submitted jobs have finished. See 
   :manpage:`bkr-job-watch(1)`.

Options for selecting a distro:

.. option:: --distro <name>

   Run the job with distro named <name>.

.. option:: --family <family>

   Run the job with the latest distro in <family>, for example 
   ``RedHatEnterpriseLinux6``.

.. option:: --variant <variant>

   Run the job with distro variant <variant>, for example ``Server``. Combine 
   this with :option:`--family`.

.. option:: --tag <tag>

   Run the job with the latest distro tagged with <tag>. Combine this with 
   :option:`--family`. By default the ``STABLE`` tag is used.

Options for selecting systems:

.. option:: --arch <arch>

   Generate a job for <arch>. This option may be specified multiple times. By 
   default, a copy of the job is generated for each arch supported by the 
   selected distro.

.. option:: --systype <type>

   Run the job on system(s) of type <type>. This defaults to ``Machine`` which 
   is almost always what you want.

.. option:: --keyvalue <name>=<value>

   Run the job on system(s) which have the key <name> set to <value>, for 
   example ``NETWORK=e1000``.

.. option:: --machine <fqdn>

   Run the job on system with <fqdn>. This option will always select a single 
   system, and so does not make sense combined with any other system options.

.. option:: --random

   Select a system at random.

Options for specifying tasks in the job:

.. option:: --package <package>

   Include tests for <package> in the job. This option may be specified 
   multiple times.

.. option:: --type <type>

   Include tasks of type <type> in the job. This option may be specified 
   multiple times.

.. option:: --task <task>

   Include <task> in the job. This option may be specified multiple times.

Options to customise the installation:

.. option:: --kernel_options <opts>

   Pass additional kernel options for during installation. The options string 
   is applied on top of any install-time kernel options which are set by 
   default for the chosen system and distro.

.. option:: --kernel_options_post <opts>

   Pass additional kernel options for after installation. The options string is 
   applied on top of any post-install kernel options which are set by default 
   for the chosen system and distro.

Options for multi-host testing:

.. option:: --clients <number>

   Use <number> clients in the job.

.. option:: --servers <number>

   Use <number> servers in the job.

Other options for modifying the job:

.. option:: --whiteboard <whiteboard>

   Set the job's whiteboard to <whiteboard>.

.. option:: --retention_tag <tag>

   Set the job's data retention policy to <tag>. This defaults to ``scratch``.

.. option:: --product <cpeid>

   Set the job's product to <cpeid>.

.. option:: --repo <url>

   Make the yum repository at <url> available during the job. This option may 
   be specified multiple times.

.. option:: --taskparam <name>=<value>

   Sets parameter <name> to <value> for all tasks in the job.

.. option:: --install <package>

   Install additional package <package> after provisioning. This uses the 
   /distribution/pkginstall task. This option may be specified multiple times.

.. option:: --cc <email>

   Add <email> to the cc list for the job(s). The cc list will receive the job 
   completion notification. This option may be specified multiple times.

.. option:: --kdump

   Turn on kdump.

.. option:: --ndump

   Turn on ndnc.

.. option:: --method <method>

   Install using <method> (``nfs`` or ``http``). The default is to use NFS.

.. option:: --priority <priority>

   Set job priority to <priority>. Can be ``Low``, ``Medium``, ``Normal``, 
   ``High``, or ``Urgent``. The default is ``Normal``.

Files
-----

On startup :program:`bkr` searches the following locations in order for its config:

    :file:`~/.beaker_client/config`

    :file:`/etc/beaker/client.conf`

Environment
-----------

The following environment variables affect the operation of :program:`bkr`.

.. envvar:: BEAKER_CLIENT_CONF

   If set to a non-empty value, this overrides the usual configuration search 
   paths. This must be the full path to the configuration file.
