.. _kickstarts:

Customizing kickstarts
======================

When Beaker provisions a system, the Beaker server generates an Anaconda
kickstart from a template file. Beaker’s kickstart templates are written
in the Jinja2 templating language. Refer to the `Jinja2
documentation <http://jinja.pocoo.org/docs/>`_ for details of the
template syntax and built-in constructs which are available to all
templates.

Beaker selects a base kickstart template according to the major version
of the distro being provisioned, for example ``Fedora16`` or
``RedHatEnterpriseLinux6``. If no template is found under this name,
Beaker will also try the major version with trailing digits stripped
(``Fedora``, ``RedHatEnterpriseLinux``).

The Beaker server searches the following directories for kickstart
templates, in order:

-  ``/etc/beaker/kickstarts``

   Custom templates may be placed here.

-  ``/usr/lib/python2.6/site-packages/bkr/server/kickstarts``

   These templates are packaged with Beaker and should not be modified.

Beaker ships with kickstart templates for all current Fedora and Red Hat
Enterprise Linux distros. The shipped templates include all the
necessary parts to run Beaker scheduled jobs. They also provide a
mechanism for customizing the generated kickstarts with template
"snippets". Administrators are recommended to use custom snippets where
necessary, rather than customizing the base templates.

Kickstart snippets
------------------

Each snippet provides a small unit of functionality within the
kickstart. The name and purpose of all defined snippets are given below.

For the following snippets Beaker ships a default template, which should
be sufficient in most cases. However, administrators may choose to
override these if necessary.

``print_anaconda_repos``
    Provides the ``repo`` kickstart commands which tell Anaconda where
    to find the distro tree’s Yum repositories for installation. This
    includes any custom repos passed in the job XML as well, e.g.
    ``<repo name="repo_id" url="http://server/path/to/repo"/>``

``install_method``
    Provides the ``url`` or ``nfs`` kickstart command which tells
    Anaconda where to find the distro tree for installation.

``lab_env``
    Sets environment variables on the installed system, giving the
    address of various services within the lab. The exact name and
    meaning of the environment variables are left up to the
    administrator, but may include for example build servers, download
    servers, or temporary storage servers.

``post_s390_reboot``
    Reportedly this does not work and should probably be deleted.

``pre_anamon``; ``post_anamon``
    Configures anamon, a small daemon which runs during the Anaconda
    install process and uploads log files to the Beaker scheduler.

``print_repos``
    Sets up the system’s Yum repo configuration after install.

``readahead_packages``; ``readahead_sysconfig``
    Disables readahead, which is known to conflict with auditd.

``rhts_devices``; ``rhts_scsi_ethdevices``
    Provides ``device`` commands (if necessary) which tell Anaconda to
    load additional device modules.

``rhts_packages``
    Provides a list of packages to be installed by Anaconda, based on
    the packages required by and requested in the recipe.

``rhts_pre``; ``rhts_post``
    Scripts necessary for running a Beaker recipe on the system after it
    is provisioned. These should never be overridden by the
    administrator.

``ssh_keys``
    Adds the Beaker user’s SSH public keys to
    ``/root/.ssh/authorized_keys`` after installation, so that they can
    log in using SSH key authentication.

``timezone``
    Provides the ``timezone`` kickstart command. The default timezone is
    "America/New\_York". Administrators may wish to customize this on a
    per-lab basis to match the local timezone of the lab

The following snippets have no default template, and will be empty
unless customized by the administrator:

``network``
    Provides extra network configuration parameters for Anaconda.

``packages``
    Can be used to append extra packages to the ``%packages`` section of
    the kickstart.

``system``; ``<distro_major_version>``
    Can be used to insert extra Anaconda commands into the main section
    of the kickstart.

``system_pre``; ``<distro_major_version>_pre``
    Can be used to insert extra shell commands into the %pre section of
    the kickstart.

``system_post``; ``<distro_major_version>_post``
    Can be used to insert extra shell commands into the %post section of
    the kickstart.

When a snippet is included in a kickstart template, Beaker tries to load
the snippet from the following locations on the server’s filesystem, in
order:

-  ``/etc/beaker/snippets/per_system/<snippet_name>/<system_fqdn>``

-  ``/etc/beaker/snippets/per_lab/<snippet_name>/<labcontroller_fqdn>``

-  ``/etc/beaker/snippets/per_osversion/<snippet_name>/<distro_version>``

-  ``/etc/beaker/snippets/per_osmajor/<snippet_name>/<distro_major_version>``

-  ``/etc/beaker/snippets/<snippet_name>``

-  ``/usr/lib/python2.6/site-packages/bkr/server/snippets/<snippet_name>``

This allows administrators to customize Beaker kickstarts at whatever
level is necessary.

For example, if the system host01.example.com needs to use a network
interface other than the default, the following snippet could be placed
in ``/etc/beaker/snippets/per_system/network/host01.example.com``:

::

    network --device eth1 --bootproto dhcp --onboot yes

Writing kickstart templates
---------------------------

All kickstart metadata variables are exposed as template variables. The
``system``, ``distro``, ``distro_tree``, ``user``, and ``recipe``
variables are the corresponding Beaker model objects loaded from the
database. (User templates do not have access to these model objects.)

In addition to the built-in template constructs provided by Jinja, the
following utilities are available in templates:

``end``
    A variable which contains the string ``%end`` if the version of
    Anaconda requires it, otherwise undefined. For compatibility across
    all Anaconda versions, templates should always terminate sections
    with this variable. For example:

    ::

        %post
        echo "All done."
        {{ end }}

``parsed_url``
    A Jinja filter which parses a URL using
    ```urlparse.urlparse`` <http://docs.python.org/library/urlparse.html#urlparse.urlparse>`_.

``re``
    The Python `re <http://docs.python.org/library/re.html>`_ module,
    for evaluating regular expressions.

``snippet``
    A function which evaluates the named snippet and returns the result.
    If no template is found for the snippet, returns a comment to that
    effect.

``split``
    A Jinja filter which splits on whitespace, or any other delimiter.
    See
    `string.split <http://docs.python.org/library/string.html#string.split>`_.

``arch``; ``osmajor``; ``osversion``
    These are Jinja tests which can be applied to ``distro_tree``. Each
    takes multiple arguments, and evaluates to true if the distro tree
    matches one of the arguments. For example:

    ::

        {% if distro_tree is arch('s390', 's390x') %}
        <...>

        {% if distro_tree is osversion('RedHatEnterpriseLinux6.0') %}
        <...>

        {% if distro_tree is osmajor('RedHatEnterpriseLinux3', 'RedHatEnterpriseLinux4') %}
        <...>

``urljoin``
    A Jinja filter which resolves a relative URL against a base URL. For
    example:

    ::

        {{ 'http://example.com/distros/'|urljoin('RHEL-6.2/') }}

    will evaluate to ``http://example.com/distros/RHEL-6.2/`` in the
    kickstart.

``var``
    A function which looks up a variable by name.


