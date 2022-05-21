What's New in Beaker 28?
========================

Beaker 28 uses Restraint as the default test harness for all OS releases,
iPXE support, enhanced installation failure detection and some other
features.

Restraint as the default harness for all distributions
------------------------------------------------------

`Restraint <https://restraint.readthedocs.io/>`_ is now the default test
harness, for all recipes. This means RHEL 5+, all currently supported
Fedora releases and Fedora Rawhide.

Support for Beah remains. You can select it by using
``harness=beah`` in the kickstart metadata of your recipes. However,
now it is necessary to add ``install_task_requires`` to kickstart
metadata if you would like to populate the ``packages`` section.

(Contributed by `Martin Styk <https://github.com/StykMartin>`_ -
`GitHub PR #46 <https://github.com/beaker-project/beaker/pull/46>`_)

Support <kickstart/> without a template
---------------------------------------

By default ``<kickstart />`` XML tag is used to add extra kickstart
command to predefined template. We noticed that it may not suit
all users; therefore, we added a support to define your own kickstart
under ``<kickstart>``. You can enable this feature with ``no_ks_template``
in your metadata.

Kickstart defined by ``<kickstart>`` will use our Jinja2 template
mechanism, therefore it is highly recommended to combine it with our
snippets. Especially with ``clear_netboot`` (Removes PXE files).

Warning: This feature bypasses common safeguards that might have been
put in place by Beaker instance administrators and might render some
systems unbootable if used incorrectly. Use with care.

For example
.. code-block:: XML

    <job retention_tag="scratch">
        <recipe whiteboard="" role="None" ks_meta="no_ks_template" kernel_options="" kernel_options_post="">
            <kickstart>
                {% snippet 'clear_netboot' %}

            </kickstart>

    </job>

(Contributed by `Martin Styk <https://github.com/StykMartin>`_ -
`Bugzilla Issue #1831885 <https://bugzilla.redhat.com/show_bug.cgi?id=1831885>`_)

iPXE support
------------

iPXE is a NIC boot ROM that can be flashed into devices, chain loaded
from other boot agents, run as a UEFI executable, booted from physical
media, etc.

In addition to extending boot support to protocols beyond
TFTP, iPXE also includes powerful scripting support. This adds support
for devices booting into the Beaker environment using that scripting
support.

The behavior here is largely modeled after PXELINUX, however
note that iPXE does not start fetching files with patterns based on
device MAC address, IP address, or any of that when it loads, nor does
it fetch a `default` file.

For more details please refer to :ref:`boot-loader-images`.

(Contributed by `Alex Williamson <https://github.com/awilliam>`_
and `Martin Styk <https://github.com/StykMartin>`_ -
`Bugzilla Issue #1788796 <https://bugzilla.redhat.com/show_bug.cgi?id=1788796>`_)

Enhanced installation failure detection
---------------------------------------

Previously, we relied on output from ``console`` to detect installation
failures. This may not work for several reasons.

* Machine is not attached to console server.
* Error strings are always changing and Beaker is unaware of new error.
* Reservesys Workflow completely ignores installation failures.

Now, we use combination of approach mentioned above and ``%onerror``
section. If installer hits a fatal error and ``%onerror`` section
is executed we abort installation automatically.

This is supported on RHEL7+ and all Fedora. However, it can be disabled
by ``disable_onerror`` defined in kickstart metadata.

(Contributed by `Martin Styk <https://github.com/StykMartin>`_ -
`GitHub PR #15 <https://github.com/beaker-project/beaker/pull/15>`_)

Multi-console log support
-------------------------

In conjunction with an external console logging system (such as
`conserver <http://www.conserver.com/>`__), Beaker also supports the
automatic capture of the console logs for the duration of provisioning
and execution of a recipe.

We decided to extend this support. Previously, Beaker was reading the
only output of file defined by ``FQDN`` for a given system.

With multi-console support, you can get output from multiple consoles.
The only requirement is that name of the file has to start with
``FQDN-``.

For example following files will be logged as console files:

* ``CONSOLE_LOGS``/test.example.com -> console.log
* ``CONSOLE_LOGS``/test.example.com-bmc -> console-bmc.log
* ``CONSOLE_LOGS``/test.example.com-serial2 -> console-serial2.log

(Contribued by `John Villalovos <https://github.com/JohnVillalovos>`_ -
`GitHub PR #11 <https://github.com/beaker-project/beaker/pull/11>`_)

Bug fixes
---------

A number of bug fixes are also included in this release:

* | `BZ#1600587 <https://bugzilla.redhat.com/show_bug.cgi?id=1600587>`_:
    Beaker CSV Export is now working properly with bigger number of
    systems and excluded families.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `BZ#1851464 <https://bugzilla.redhat.com/show_bug.cgi?id=1851464>`_:
    Beaker is now properly handling XML element ``type`` when it is used
    in Job XML.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `BZ#1803555 <https://bugzilla.redhat.com/show_bug.cgi?id=1803555>`_:
    Multiple definitions of ``harness`` kickstart metadata are handled
    properly. All packages are installed by YUM/DNF.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `BZ#1796851 <https://bugzilla.redhat.com/show_bug.cgi?id=1796851>`_:
    Size for kickstart was extended. From previous 65535 characters to
    16777215. When new size limit is breached job is automatically
    aborted to keep sane state in Beaker Scheduler.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `BZ#1711063 <https://bugzilla.redhat.com/show_bug.cgi?id=1711063>`_:
    New documentation introduced for disabling default kernel cmdline
    options.
  | (Contributed by `Carol Bouchard <https://github.com/cbouchar>`_)
* | `GH#58 <https://github.com/beaker-project/beaker/issues/58>`_:
    User is now able to control ``skip_if_unavailable`` for Task Repo.
    Value can be set via ``skip_taskrepo`` kickstart metadata.
    Default value is 0.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#48 <https://github.com/beaker-project/beaker/issues/48>`_:
    Password is now hidden by default in power management settings.
    However, it can be revealed if necessary.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#36 <https://github.com/beaker-project/beaker/issues/36>`_:
    Extended support for ``system-modify`` cli command.
    Now ``system-modify`` can modify any power management settings.
  | (Contributed by `John Villalovos <https://github.com/JohnVillalovos>`_)
* | `GH#28 <https://github.com/beaker-project/beaker/issues/28>`_:
    Removed issue with ``beaker-expire-distros --remove-all`` where
    error appears instead of removing all distributions.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#24 <https://github.com/beaker-project/beaker/issues/24>`_:
    ``beaker-import`` is now able to keep previously defined
    kernel_options, kernel_options_post, and ks_meta.
  | (Contributed by `John Villalovos <https://github.com/JohnVillalovos>`_)
* | `GH#19 <https://github.com/beaker-project/beaker/issues/19>`_:
    Authentication cookies are persistent now.
  | (Contributed by `John Villalovos <https://github.com/JohnVillalovos>`_)
* | `GH#17 <https://github.com/beaker-project/beaker/issues/17>`_:
    Alternative Harness API was extended. Now, Beaker supports
    power commands via API.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)

Beaker 28.1
~~~~~~~~~~~
* | `GH#74 <https://github.com/beaker-project/beaker/issues/74>`_:
    Beaker client now works with Python 3.9. Deprecated python
    functions were removed.
  | (Contributed by `Xavi Hernandez <https://github.com/xhernandez>`_)
* | `GH#76 <https://github.com/beaker-project/beaker/issues/76>`_:
    Beaker server no longer generates kickstart with ``install``
    kickstart command for RHEL6+.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#79 <https://github.com/beaker-project/beaker/issues/79>`_:
    When provisioning a RHEL 9 machine, the root user can
    use SSH to log in to the machine, using a password or key.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#80 <https://github.com/beaker-project/beaker/issues/80>`_:
    Beaker server no longer requires qpid package by default.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)

Beaker 28.2
~~~~~~~~~~~
* | `GH#90 <https://github.com/beaker-project/beaker/issues/90>`_:
    Replace deprecated kernel options for newer distros.
  | (Contributed by `Renan Barbosa <https://github.com/renanrodrigo/>`_)
* | `GH#86 <https://github.com/beaker-project/beaker/issues/86>`_:
     Get console logs raises exception for guest recipes.  Change
     made to not get console log if system name is not available.
  | (Contributed by `Carol Bouchard <https://github.com/cbouchar>`_)

Beaker 28.3
~~~~~~~~~~~
* | `GH#141 <https://github.com/beaker-project/beaker/issues/141>`_:
    Enable Beaker Client to build for CentOS 9 Stream. Python nose
    was replaced with pytest.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#143 <https://github.com/beaker-project/beaker/issues/143>`_:
    Kickstart no longer contains `%onerror` section on RHEL <= 7.3
    as it is not supported.
  | (Contributed by `Matej Dujava <https://github.com/mdujava>`_)
