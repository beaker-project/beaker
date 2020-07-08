Tasks provided with Beaker
--------------------------

Besides the custom tasks which Beaker users would write for a specific
testing scenario, there are a number of tasks which are distributed
and maintained along with Beaker. Among these,
the ``/distribution/check-install`` and ``/distribution/reservesys`` tasks are
essential for Beaker's operation. The ``/distribution/inventory`` task is not
essential for Beaker's operation, but it is required for accurate
functioning of Beaker's ability to schedule jobs on test systems
meeting user specified hardware criteria. The
``/distribution/beaker/dogfood`` task runs Beaker's test suite (hence, the
name `dogfood`) and is perhaps only useful for meeting certain
specific requirements of the Beaker developers.


/distribution/check-install
===========================

The purpose of this task is to report back on the system install
(provisioning). It is usually added before any scenario specific tasks
so that it is run immediately after the system has been provisioned.

This task collects and reports various information about the installed system
which may be useful in debugging any problems with the installer or the distro.

.. _reservesys-task:

/distribution/reservesys
========================

The ``/distribution/reservesys`` task reserves a system for a specific
time frame to aid post-test analysis. You would usually append this
task in your recipe so that the system is available for you to login
after the other tasks have been run, but before the system is
returned to Beaker. :ref:`system-reserve` describes system reservation
in detail.

.. _inventory-task:

/distribution/inventory
=======================

The ``/distribution/inventory`` task is useful for the administrator of
a Beaker installation to gather detailed hardware data about
Beaker's test systems. Hardware devices which are probed include disk
drives, graphics hardware and network devices. When this task is run
on a test system, it retrieves this information and sends it to the Beaker
server where it is updated in the main database.

This data can then be used by Beaker to schedule a job for which a
specific hardware requirement may have been specified (See:
:ref:`device specification in jobs <device-specs>`). Hence, it is a
good idea to run this task on every system to ensure that the hardware
details are correctly updated in Beaker's database.

.. _command-task:

/distribution/command
=====================

The ``/distribution/command`` task runs an arbitrary shell command, given in
the ``CMDS_TO_RUN`` parameter.

This task is useful for inserting ad hoc tests or behaviour into a recipe for
experimentation purposes, without needing to modify an existing task or write
a new one.

For example, to log the CPU information of the system under test::

    ...
    <task name="/distribution/command">
        <params>
            <param name="CMDS_TO_RUN" value="cat /proc/cpuinfo" />
        </params>
    </task>
    ...


/distribution/beaker/dogfood
============================

The ``/distribution/beaker/dogfood`` task runs Beaker's test suite (unit
tests and selenium tests) on a test system. It can be configured to
either run the tests from the development branch of Beaker or the most
recent released version.

This task is used by the Beaker developers to run the test suite
every time a new patch is pushed to the development branch to help
prevent any regressions in the code base.

.. _dummy-task:

/distribution/utils/dummy
=========================

This is a placeholder task used to align task execution across different
recipes in a multi-host recipe set. See :ref:`multihost-tasks` for details.


.. _virt-install-task:

/distribution/virt/install
==========================

The ``/distribution/virt/install`` task is responsible for installing
a virtual machine (defined as a 'guest recipe' in Beaker). It does this via
``virt-install``. The task is defined in the host recipe, often along with
``/distribution/virt/start``. For example::

  <task name="/distribution/check-install" role="SERVERS">
    <params/>
  </task>
  <task name="/distribution/virt/install" role="SERVERS">
    <params/>
  </task>
  <task name="/distribution/virt/start" role="SERVERS">
    <params/>
  </task>

Be aware that ``/distribution/virt/start`` and ``/distribution/virt/install``
should never be defined in the guest recipe itself.


.. _virt-image-install-task:

/distribution/virt/image-install
================================

This task is an experimental alternative to the regular
``/distribution/virt/install`` task for installing guest recipes. Rather than
booting the installer inside the guest and running through a complete
installation, this task fetches a cloud image and boots that.

The ``CLOUD_IMAGE`` task parameter should be the URL for a suitable cloud
image. The image must have the ``cloud-init`` package pre-installed and
enabled. This task approximates the effect of the guest kickstart by generating
a suitable user-data file for cloud-init.

Note that there are a number of limitations when using this task:

* The distro tree selected by Beaker for the guest recipe is effectively
  ignored. The distro used in the guest is determined solely by what image is
  given.

* Similarly, it is the job submitter's responsibility to use a suitable local
  mirror for the cloud image. (Fetching the image over an expensive WAN link is
  not desirable but Beaker will not prevent it.)

* Not all parts of the guest kickstart are accurately applied, since the
  installer is skipped. The task extracts ``%packages`` and ``%post`` sections,
  and it also handles the ``repo``, ``rootpw``, and ``selinux`` commands.

.. _virt-start-task:

/distribution/virt/start
========================

The ``/distribution/virt/start`` task is used for starting a virtual machine,
via ``virsh start``. Please see :ref:`virt-install-task` for examples on how to
use it with ``/distribution/virt/install``.

.. _distribution-rebuild-task:

/distribution/rebuild
=====================

This task is for experimental mass rebuilds of an entire distribution from
source, for example using a newer or modified build toolchain. It fetches
source RPMs from a given yum repo and rebuilds them all in mock.

Packages are rebuilt in alphabetical order. This task does not attempt to build
packages in dependency order, nor does it inject the build results back into
the build root.

The following task parameters are accepted:

``SOURCE_REPO``
    URL of the yum repo to fetch source RPMs from.
``MOCK_REPOS``
    Space-separated list of URLs of the yum repos to include in the build root.
    Typically this should include the entire distribution or the build tag for
    it. You can also add extra repos containing patched packages.
``MOCK_CHROOT_SETUP_CMD``
    Command to be run when mock sets up the chroot. The default value is
    suitable for Fedora: ``install @buildsys-build``. The group name may need
    adjusting for other distros.
``MOCK_TARGET_ARCH``
    Target architecture for builds. By default this will match the arch of the
    recipe where this task is running.
``MOCK_CONFIG_NAME``
    Name of the mock configuration to use or generate (excluding ``.cfg`` file
    extension).
    If this parameter is set and the configuration exists, it will be used as
    is. Otherwise the configuration will be generated based on the parameters
    above.
``SKIP_NOARCH``
    If set to a non-empty value, skip building any SRPMs which produce only
    noarch packages.
``KEEP_RESULTS``
    If set to a non-empty value, keep the results (RPMs and log files) produced
    by each build in
    :file:`/mnt/tests/distribution/rebuild/results/{packagename}/`.
    You can use a subsequent task in the recipe to examine the results or copy
    the RPMs elsewhere.
``SRPM_BLACKLIST``
    SRPMs to skip.
    This parameter must be a whitespace-separated list of `bash glob patterns
    <http://www.gnu.org/software/bash/manual/bashref.html#Pattern-Matching>`_.
    Each pattern is matched against the SRPM filename (including .src.rpm
    extension). If any pattern matches, the SRPM is skipped. For example
    ``kernel*`` will skip any SRPMs beginning with kernel.
``SRPM_WHITELIST``
    SRPMs to build. If this parameter is set, any SRPM which does not match
    a pattern in the whitelist is skipped.
    Similar to ``SRPM_BLACKLIST``, this must be a whitespace-separated list of
    bash glob patterns.

As an example, imagine you have built the latest GCC version 99.0, and you want
to try rebuilding all architecture-specific packages in Fedora 21 using the new
compiler to see if it introduces any build failures:

.. code-block:: xml

    <task name="/distribution/rebuild" role="STANDALONE">
        <params>
            <param name="SOURCE_REPO"
                   value="http://dl.fedoraproject.org/pub/fedora/linux/releases/21/Everything/source/SRPMS/" />
            <param name="MOCK_REPOS"
                   value="http://dl.fedoraproject.org/pub/fedora/linux/releases/21/Everything/x86_64/os/
                          http://example.com/my-gcc99-test-repo/" />
            <param name="SKIP_NOARCH" value="1" />
        </params>
    </task>

Task source code
================

The source code for the above tasks can be found in the
`Beaker core tasks git repo`_.  The tasks for testing Beaker itself are
in the `Beaker meta tasks git repo`_.

.. _Beaker core tasks git repo: https://github.com/beaker-project/beaker-core-tasks/
.. _Beaker meta tasks git repo: https://github.com/beaker-project/beaker-meta-tasks/
