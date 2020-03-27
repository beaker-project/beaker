What's New in Beaker 27?
========================

Beaker 27 has Python 3 support for beaker-common and beaker-client, AMQ messaging,
several changes for outdated packages and some other features.


Moving towards new distros and Python 3
---------------------------------------

Python 2 is going to be discontinued in upstream soon, and there is a need to
move the Beaker code to Python 3. In this release, the code for Common and Client
is adapted to run in both versions of Python. It is the first step towards the
upcoming upgrade of the whole Beaker project.

Projects as RHTS were also ported to Python 3 to solve compatibility issues.

Some distributions, such as the newer Fedoras, do not even have Python2 installed.
RHEL8 has packages for Python 3. This version of Beaker, with the Python 3 code,
can be built on Fedora 30+ and RHEL8.

Due to package updates (see below) the system requirements for the build have
RHEL 7.7 as a minimum, to ensure that we have all the packages for compatibility,
as well as DNF and full support for Python 3 itself.

(Contributed by Martin Styk in :issue:`1455424` and Renan Rodrigo Barbosa
in :issue:`1750646`)


AMQP and new features
---------------------

Until now it was necessary to pool job(s) to get the current status.

We decided to implement a complementary solution to get the latest status updates in
your Beaker instance. Now, you can read AMQP messages in your topic. Messages are
emitted automatically after scheduler updates status for Recipe/Job/RecipeSet/Recipe/Task.

It is expected that AMQP bus is already running in your infrastructure. Integration can be
configured in `server.cfg <https://beaker-project.org/docs/admin-guide/config-files.html>`_.

(Contributed by Martin Styk in :issue:`1370383`)


GRUB2 functionality is extended
-------------------------------

We are expanding our functionality with menus. In Beaker 27 we added a new menu for
PPC64(LE) architecture. The menu can be used as the default option for GRUB2 PPC64(LE)
configuration.

You can find the new menu in :code:`<tftp_folder>/boot/grub2/beaker_menu_ppc64.cfg` or
:code:`beaker_menu_ppc64le.cfg.`

Besides that, the configuration for the bootloader folder was improved to be more reliable. Support
for x86_64 architecture and fixes to PXELINUX boot were added.

For more information refer to the `TFTP Configuration <https://beaker-project.org/docs/admin-guide/tftp.html>`_ guide.

(Contributed by Martin Styk in :issue:`1779202` and :issue:`1778839`)


Moving repositories to Github
-----------------------------

All of the repositories for the Beaker code base are being migrated to Github. Some
pieces are already there, and the Beaker repository itself is going to
leave Gerrit as well.

Examples of repositories that have Github fully enabled are the the
`meta tasks <https://github.com/beaker-project/beaker-meta-tasks>`_,
`core tasks <https://github.com/beaker-project/beaker-core-tasks>`_ and
`Beaker infrastructure <https://github.com/beaker-project/beaker-infrastructure>`_.

Now we have templates for issues and configuration for Stickler to lint the code on
pull requests for the Beaker repository.

(Contributed by Martin Styk)


Outdated packages were replaced
-------------------------------

Many older packages are being updated to newer versions or replaced by up-to-date
equivalents. Those changes may be smaller, such as the jinja2 version update,
but also may include bigger changes such as removing TurboGears from the kickstarts.

Tests are updated with the removal of the unittest2 dependency and adaptation to
the unittest package. cracklib was changed to pwquality, aiming at RHEL7 servers.
python-krbV was replaced by python-gssapi.

The Auth module now is driven by a flask API. Also, all of the YUM dependencies are
removed, and Beaker can use DNF to manage the RPMs. Besides the DNF API being
more concise, YUM is EOL’d and might be removed for newer versions of Fedora.

(Contributed by Martin Styk in :issue:`1642145`, :issue:`1120434`,
:issue:`1455425` and :issue:`1455425` and Renan Rodrigo Barbosa in :issue:`1597956`
and :issue:`1622791`.)


BEAH is sunsetted
-----------------

With the adoption of `restraint <https://restraint.readthedocs.io/>`_
and after the release of :doc:`Beaker 26 <./release-26>` which defined it as the
default test harness for newer distributions, the next step is to sunset BEAH.
Users should start migrating BEAH based jobs to restraint.

BEAH is marked as EOL’d and will neither receive new patches nor get support anymore.


Bug fixes
---------

A number of bug fixes are also included in this release:

* | :issue:`1777817`: Job and Recipe whiteboards now have a bigger character limit.
  | (Contributed by Martin Styk)
* | :issue:`1662898`:  Beaker is now properly ignoring SSL certificate verification
    when the :program:`--insecure` switch is provided in the command line.
  | (Contributed by Martin Styk)
* | :issue:`1723692`:  Beaker-client is now providing the way how to check the machine
    history of activity. You can use :program:`bkr system-history-list <FQDN>`.
  | (Contributed by Martin Styk)
* | :issue:`1703371`: Tests were updated to convert a list of Arch instances to the
    respective Arch names in unicode format, as SQLAlchemy versions greater than 1.1
  | will need this for comparison.
  | (Contributed by Martin Styk)
* | :issue:`1703367`: Group passwords now need 8 characters on Fedora systems to be
    compliant with the PWQuality version.
  | (Contributed by Martin Styk)
* | :issue:`1671054`: Change integration tests to use sessions to connect to Openstack.
  | (Contributed by Martin Styk)
* | :issue:`1776324`: The bash-completion script for the beaker client has been rewritten.
    Changes include speed improvements using a cache directory, ability to specify file names for
    commands which take files and option parsing.
  | (Contributed by John L. Villalovos)
* | :issue:`1776325`: Update Frontend for OpenStack integration
  | (Contributed by Martin Styk)
* | :issue:`1776327`: Set the correct MIME type for the kickstart endpoint.
  | (Contributed by Martin Styk)
* | :issue:`1404909`: Added visibility support for iPXE image creation, enabling users to
    create and upload private images, for instance.
  | (Contributed by Martin Styk)
* | :issue:`1776332`: OpenStack flavors are now correctly filtered according
    to disk size: should now be greater or equal to 10G.
  | (Contributed by Martin Styk)
* | :issue:`1384903`: RNC schemas for task and job XML files were added to
    beaker-common.
  | (Contributed by Martin Styk)
* | :issue:`1776337`: Beaker will now pick the appropriate Kerberos credentials
    cache when authenticating.
  | (Contributed by Martin Styk)
* | :issue:`1758124`: When provisioning a Fedora 31 machine, the root user can
    use SSH to log in to the machine, using a password or key.
  | (Contributed by Martin Styk)
* | :issue:`1698383`: The Import Distro Tree web page and the distro-import
    CLI now behave the same, using the same code: duplicates are being handled
    correctly and URL checking works for both versions.
  | (Contributed by Matej Dujava and Tomas Klohna)
* | :issue:`1761195`: The way :program:`beakerd` chooses an OpenStack flavor applies
    smallest disk size and RAM memory as criteria. As there may be more than
    one flavor with the same disk size and RAM, the smallest flavor ID is now
    also used.
  | (Contributed by Georgii Karataev)
* | :issue:`1748307`: When deleting a job by clicking the "delete" button on the jobs
    list, the ID of the job will be shown on the title of the message box.
  | (Contributed by Renan Rodrigo Barbosa)
* | :issue:`719536`: All of the "excluded families" page was redesigned. Previously, any
    excluded major distributions and the respective minors had to be clicked individually,
    on a potentially huge list of checkboxes.
    This list has been reorganized and categorized, toggle buttons were added to ease
    the selection, and the major distro families can be filtered through user input.
  | (Contributed by Renan Rodrigo Barbosa)
* | :issue:`662517`: The Reserve Workflow page now shows a warning about available
    lab controllers which don't support any of the selected distro trees.
  | (Contributed by Renan Rodrigo Barbosa)
* | :issue:`657559`: When user specific variant but no arch on command line,
    he would incorrectly get all arches across all variants. This has now been fixed
    and variant will correctly output only possible arches that are present.
  | (Contributed by Tomas Klohna)
* | :issue:`1694004`: The Beaker inventory_osmajors defaults were updated:
    systems as Fedora 21, Fedora 22, CentOS5 and RHEL5 are out of the list and
    Fedora 29, Fedora 30, Fedora 31 and RHEL8 were added.
  | (Contributed by Georgii Karataev)


Beaker 27.1
~~~~~~~~~~~
* | :issue:`1761589`: Added new option 'no_networks' to ks_meta.
    This option can be useful when user already defines IP stack on
    kernel options.
  | (Contributed by Martin Styk)
* | :issue:`1793655`: Updated default Apache configuration for deployment.
  | (Contributed by Martin Styk)
* | :issue:`1791205`: Fixed status code for task status update endpoint.
    Instead of returning 500 endpoint will return 409 in case status
    is already updated.
  | (Contributed by Martin Styk)
* | :issue:`1795234`: Added support for enabling/disabling firstboot in kickstart.
  | (Contributed by Martin Styk)
* | :issue:`1780909`: Fixed upstream spec file. DNF is now installed as part
    of Lab Controllers.
  | (Contributed by Martin Styk)
* | :issue:`1795912`: Improved proxy logging in Lab Controllers.
    All traffic is captured in logs instead of XMLRPC only.
  | (Contributed by Martin Styk)
* | :issue:`1778643`: Improved kernel panic detection.
  | (Contributed by Renan Rodrigo Barbosa)


Beaker 27.2
~~~~~~~~~~~
* | :issue:`1807755`: Added support to remove OpenStack Keystone Trust even
    when OpenStack integration is disabled.
  | (Contributed by Martin Styk)
* | :issue:`1793655`: Beaker-client is now using `distribution/check-install` task
    for all OS distributions. This is a replacement for `distribution/install`.
  | (Contributed by Martin Styk)


Beaker 27.3
~~~~~~~~~~~
* | :issue:`1814761`: Updated default values for kickstart. This change is
    necessary to enable provision on Fedora 32+.
  | (Contributed by Martin Styk)
* | :issue:`1814784`: Improved stability in beaker-proxy. Now, WSGI layer
    of beaker-proxy is capable of closing all sockets imminently after
    request is finished.
  | (Contributed by Martin Styk)

Beaker 27.4
~~~~~~~~~~~
* | :issue:`1816102`: New command for beaker-client introduced.
    Beaker-client is providing the way how to remove a task from task
    library based on the name. This feature is limited to administrators.
    You can execute as following `bkr task-remove <name>`.
  | (Contributed by Martin Styk)
* | :issue:`1795917`:  Added support to use different variable for kickstart
    on kernel cmdline. Now user can define new `ks_meta` with name
    `ks_keyword`.
  | (Contributed by John Villalovos)
* | :issue:`1818070`: Now, distribution RHVH is imported by default with
    additional `ks_meta` variable `ks_keyword='inst.ks'`. This mitigates
    problems with an older version of RHVH where `ks` do not trigger
    the installation process in RHVH, instead of that, it is considered
    an upgrade.
  | (Contributed by Martin Styk)
