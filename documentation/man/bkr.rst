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


.. include:: subcommands.rst

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
    TR
        task-result

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

.. option:: --insecure

   Skip all SSL certificate validity checks. This allows the client to connect 
   to a Beaker server with an invalid, expired, or untrusted SSL certificate.

.. option:: --username <username>

   Authenticate using password authentication, with <username>. If a password 
   is not given using :option:`--password`, the user is prompted for the 
   password on stdin.

   This option overrides the authentication type specified in the configuration 
   file, forcing password authentication to be used.

.. option:: --password <password>

   Authenticate using <password>. This option is only applicable when 
   :option:`--username` is also passed.

.. option:: --proxy-user <username>

   Impersonate <username> in order to perform actions on their behalf.

   This option can only be used when the authenticating user is a member of
   a group which has been granted 'proxy_user' permission by the Beaker
   administrator. Typically this permission is granted to service accounts
   so that a trusted script can perform actions on behalf of any other
   Beaker user.

.. option:: --help

   Show a brief summary of the command and its available options then exit.

.. _workflow-options:

Workflow options
****************

These options are applicable to :program:`bkr` workflow subcommands, such as 
:program:`bkr workflow-simple`.

.. option:: --dry-run, --dryrun

   Don't submit the job(s) to Beaker.

.. option:: --debug

   Print the generated job XML before submitting it to Beaker.

.. option:: --pretty-xml, --prettyxml

   Pretty-print the generated job XML in a human-readable form (with 
   indentation and line breaks).

.. option:: --wait

   Watch the newly submitted job(s) for state changes and print them to stdout. 
   The command will not exit until all submitted jobs have finished. See 
   :manpage:`bkr-job-watch(1)`.

.. option:: --no-wait, --nowait

   Do not wait on job completion [default].

.. option:: --quiet

   Be quiet, don't print warnings.

Options for selecting distro tree(s):

.. option:: --family <family>

   Run the job with the latest distro in <family> (for example: ``RedHatEnterpriseLinux6``).

.. option:: --tag <tag>

   Run the job with the latest distro tagged with <tag>. Combine this with 
   :option:`--family`. By default the ``STABLE`` tag is used.

.. option:: --distro <name>

   Run the job with distro named <name>. If the given name includes 
   a % character, it is interpreted as a SQL LIKE pattern (the % character 
   matches any substring).

.. option:: --variant <variant>

   Run the job with distro variant <variant>, for example ``Server``. Combine 
   this with :option:`--family`.

.. option:: --arch <arch> 

   Use only <arch> in job. By default, a recipe set is generated for
   each arch supported by the selected distro. This option may be
   specified multiple times. 

Options for selecting system(s):

.. option:: --machine <fqdn>

   Run the job on system with <fqdn>. This option will always select a single 
   system, and so does not make sense combined with any other system options.

.. option:: --ignore-system-status

   Always use the system given by --machine, regardless of its status.

.. option:: --systype <type>

   Run the job on system(s) of type <type>. This defaults to ``Machine`` which 
   is almost always what you want. Other supported values are
   ``Laptop``, ``Prototype`` and ``Resource``. ``Laptop`` type would be
   used to select a system from the available laptop
   computers. Similarly, ``Resource`` and ``Prototype`` would be used in cases
   where you would want to schedule your job against a system whose
   type has been set as such.

.. option:: --hostrequire "<tag> <operator> <value>"

   Additional ``<hostRequires/>`` for the job. For example, 
   ``labcontroller=lab.example.com`` would become ``<labcontroller op="=" 
   value="lab.example.com"/>`` in the job XML.

   For more advanced filtering (for example using ``<device/>``) you can also 
   pass raw XML directly to this option. Any value starting with ``<`` is 
   parsed as XML and inserted directly into ``<hostRequires/>``.

   See :ref:`job-xml` for more information about the ``<hostRequires/>`` 
   element.

.. option:: --host-filter <name>

   Look up the pre-defined host filter with the given name,and
   add the corresponding XML snippet to ``<hostRequires/>``.

   You can use pre-defined host filters as a short-hand for complicated
   or difficult to remember XML snippets.
   Beaker includes many pre-defined filters for different types of
   hardware. For example, pass ``--host-filter=INTEL__FAM15_CELERON``
   to filter for hosts with an Intel Celeron CPU.

   Filter definitions are read from the following configuration
   files:

   * :file:`/usr/lib/python2.{x}/site-packages/bkr/client/host-filters/*.conf`
   * :file:`/etc/beaker/host-filters/*.conf`
   * :file:`~/.beaker_client/host-filter`

   Files within each directory are processed in lexicographical
   order. The files contain one filter definition per line, consisting
   of the filter name and the associated XML snippet separated by whitespace.
   If the same filter name appears in multiple files, the last
   definition overrides earlier definitions.

.. option:: --keyvalue "<name> <operator> <value>"

   Run the job on system(s) which have the key <name> set to <value>
   (for example: ``NETWORK=e1000``). 

.. option:: --random

   Select a system at random. The systems owned by the user are first
   checked for availability, followed by the systems owned by the
   user's group and finally all other systems.

Options for selecting tasks:

.. option:: --task <task>

   Include <task> in the job. This option may be specified multiple times.

.. option:: --taskfile <filename>

   Include tasks listed in <filename>, each line contains one task name. Lines
   not starting with '/' are ignored.

.. option:: --package <package>

   Include tests for <package> in the job. This option may be specified 
   multiple times.

.. option:: --task-type <type>

   Include tasks of type <type> in the job. This option may be specified 
   multiple times.

.. option:: --install <package>

   Install additional package <package> after provisioning. This uses the 
   ``/distribution/pkginstall`` task. This option may be specified
   multiple times.

.. option:: --kdump

   Enable ``kdump`` using using ``/kernel/networking/kdump``.

.. option:: --ndump

   Enable ``ndnc`` using using ``/kernel/networking/ndnc``.

.. option:: --suppress-install-task

   Omit the installation checking task.

   By default, the first task in the recipe will be 
   ``/distribution/check-install``. The purpose of this task is
   to check that the operating system was installed successfully and report 
   back on any potential problems, and to collect information about the 
   installed system for debugging.

   Pass this option if you do not want this task to be implicitly inserted at 
   the start of the recipe.

Options for job configuration:

.. option:: --job-owner <username>

   Submit the job on behalf of <username>. The job will be owned by <username> 
   rather than the submitting user.

   The submitting user must be a submission delegate of <username>. Users can 
   add other users as submission delegates on their :guilabel:`Preferences` 
   page in Beaker's web UI.

.. option:: --job-group <group>

   Associate the job with <group>. This will allow other group members to 
   modify the job.

.. option:: --whiteboard <whiteboard>

   Set the job's whiteboard to <whiteboard>.

.. option:: --taskparam <name>=<value>

   Sets parameter <name> to <value> for all tasks in the job.

   .. versionadded:: 0.14.3

.. option:: --ignore-panic 

   Disable kernel panic detection and install failure detection for the recipe. 
   By default if a kernel panic appears on the serial console, or a fatal 
   installer error appears during installation, the recipe is aborted. When 
   this option is given, the messages are ignored and the recipe is not 
   aborted.

.. option:: --reserve

   Reserve the system at the end of the recipe, for further testing or 
   examination. The system will be reserved when all tasks have completed 
   executing, or if the recipe ends abnormally. Refer to :ref:`reservesys`.

.. option:: --reserve-duration <seconds>

   When :option:`--reserve` is used, this option controls the duration for the 
   reservation. The default duration is 86400 seconds (24 hours).

.. option:: --cc <email>

   Add <email> to the cc list for the job(s). The cc list will receive the job 
   completion notification. This option may be specified multiple times.

.. option:: --priority <priority>

   Set job priority to <priority>. Can be ``Low``, ``Medium``, ``Normal``, 
   ``High``, or ``Urgent``. The default is ``Normal``.

.. option:: --retention-tag <tag>
 
   Specify data retention policy for this job [default: Scratch]

.. option:: --product <product>

   Associate job with <product> for data retention purposes.

Options for installation:

.. option:: --method <method>

   Installation source method (nfs, http, ftp) [default: nfs].

.. option:: --kernel-options <opts>

   Pass additional kernel options for during installation. The options string
   is applied on top of any install-time kernel options which are set by 
   default for the chosen system and distro.

.. option:: --kernel-options-post <opts>

   Pass additional kernel options for after installation. The options string is 
   applied on top of any post-install kernel options which are set by default 
   for the chosen system and distro.
 
.. option:: --ks-append <commands>

   Specify additional kickstart commands to add to the base kickstart file.

.. option:: --ks-meta <options>

   Pass kickstart metadata <options> when generating kickstart.

.. option:: --repo <url>

   Make the yum repository at <url> available during initial installation of
   the system and afterwards. This option may be specified multiple times.
   The installation may fail if the repo is not actually available.

.. option:: --repo-post <url>

   Make the yum repository at <url> available AFTER the installation. This 
   option may be specified multiple times. The repo config will be appended to
   the kickstart's %post section. Whether or not the installation succeeds is
   not affected by the availability of the repo.

.. option:: --kickstart <filename>

   Use this kickstart template for installation. Templates are rendered on the
   server. Refer to the :ref:`custom-kickstarts` section in Beaker's 
   documentation for details about the templating language and available 
   variables. You can also pass raw kickstarts in - if you don't use any Jinja2 
   variable substitution syntax, the rendering process will reproduce the 
   template verbatim.

   If the template provides the following line::

       ## kernel_options: <options>

   the specified kernel options will be appended to existing ones defined with 
   :option:`--kernel-options`.

Options for multi-host testing:

.. option:: --clients <number>

   Use <number> clients in the job.

.. option:: --servers <number>

   Use <number> servers in the job.

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
