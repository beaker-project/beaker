.. _makefile:

Beaker Makefile
===============

This guide provide in depth information for the required and optional
Makefile variables in an Beaker test. A sample Makefile is copied into
the local directory when rhts-create-new-test tool is invoked (or can be
found at ``/usr/share/doc/beaker-devel-x.y/Makefile.template``).

``PACKAGE_NAME``
----------------

::

    # The name of the package under test:
        PACKAGE_NAME=gcc

The package under test is the common command or executable being tested.
This must be the name of an installable RPM in the distribution. If the
focus of your test is a third party application, set PACKAGE\_NAME equal
to the primary package used by the third party application. For example,
if you are writing a Beaker test to test a web application based on CGI,
set PACKAGE\_NAME to perl.

``TOPLEVEL_NAMESPACE``
----------------------

::

    # The toplevel namespace within which the test lives.
        TOPLEVEL_NAMESPACE=CoreOS

The ``Makefile`` contains three hierarchies resembling file systems,
each with their own collections of paths. In order to ensure consistency
between test creators and tests, the provided ``Makefile`` should be
used to manage these hierarchies. Thus, the scheme in the ``Makefile``
template does all the work.

For clarity, it is worth noting the hierarchies at this time:

-  *installation* tests are built as packages for clean deployment on
   test machines. More than one test can be run on a given machine, so
   there is a hierarchy below /mnt/tests which keeps the files of the
   individual tests separate from each other. This is set in each test's
   Makefile.

-  *result namespace* a hierarchical namespace for results. For example,
   tests relating to the kernel report their results somewhere within
   the /kernel subtree, and tests relating to the NFS file system (as a
   part of the kernel) report their results inside
   /kernel/filesystems/nfs/. Each test "owns" a subtree of the
   namespace, specified by the Name: field of the metadata. Many tests
   report only a single result, but it is possible for a test to write
   out a complex hierarchy of results below its subtree.

The following top level reporting namespaces are predefined and should
used to ensure consistent reporting of test results. These are the only
valid accepted namespaces.

-  *distribution* contains tests that involve the distribution as a
   whole, or a large number of packages, for example
   ``/distribution/standards/posixtestsuite``

-  *kernel* contains tests results relating to the kernel, for example
   ``/kernel/xen/xm/dmesg``

   -  The kernel namespace is unique in that it is also the name of a
      package. In this case it is usually best to define the
      ``TOPLEVEL_NAMESPACE`` like this:

      ::

          # The toplevel namespace definition for kernel tests
                        TOPLEVEL_NAMESPACE=$(PACKAGE_NAME)

-  *Desktop* contains tests results relating to desktop packages, for
   example ``/desktop/evolution/first-time-wizard-password-settings``,
   which is a specific test relating to evolution

-  *Tools* contains tests results relating to the tool chain, for
   example ``/tools/gcc/testsuite/3.4``

-  *CoreOS* all test results relating to user-space packages not covered
   by any of the above namespaces

-  *Examples* example tests that illustrate usage and functionality and
   are not actively maintained. This is a good place to experiment when
   you are getting hang of Beaker or to place simple examples to help
   others.

``RELATIVE_PATH``
-----------------

::

                       # The path of the test below the package:
                         RELATIVE_PATH=example-compilation 

An implementation of Beaker should run the test from the directory
containing the ``runtest.sh``, as listed in the ``RELATIVE_PATH`` file
of the ``Makefile``. If the test needs to move around, store this
somewhere with ``DIR=pwd`` or use ``pushd`` and ``popd``.

.. _makefile-testversion:

``TESTVERSION``
---------------

::

                   # Version of the Test. Used with make tag.
                    export TESTVERSION=1.0

This is used when building a package of a test, and provides the
"version" component of the RPM name-version-release triplet.

-  The value must be valid as an RPM version string.

-  It may consist of numbers, letters, and the dot symbol.

-  It may not include a dash symbol this is used by RPM to delimit the
   version string within the name-version-release triplet.

When writing a test from scratch, use 0.1 and increment gradually until
the test has reached a level of robustness to merit a "1.0" release.
When wrapping a test from an upstream location, use the upstream version
string here, as closely as possibly given the restrictions on valid
characters. The version should be incremented each time a change is made
to the ``Makefile`` or test files and a RPM is created from these files
to be publicly consumed in a test review or submission to a lab
scheduler.

``TEST``
--------

::

                      # The compiled namespace of the test.
                      export TEST=$(TOPLEVEL_NAMESPACE)/$(PACKAGE_NAME)/$(RELATIVE_PATH)

This variable defines the path to a test. This path should also be the
same in source control.

``BUILT_FILES``
---------------

::

    BUILT_FILES=hello-world

List the files that need to be compiled to be used in the test.

FILES
-----

::

               FILES=$(METADATA) runtest.sh Makefile PURPOSE hello-world.c \
                         verify-hello-world-output.sh

List all of the files needed to run the test to insure that there are no
packaging errors when the test is built binaries should be pulled in via
BUILT\_FILES.

Targets
-------

Each test must supply a run target which allows an implementation of the
framework to invoke ``make run``. It is usually best to have this as the
first target defined in the ``Makefile`` so that a simple invocation of
``make`` will use it as the default, and run the test. Note how the
``build`` target is set up as a dependency of run to ensure that this
happens if necessary.

Additional targets and variables supplied by the include for
``/usr/share/beaker/lib/beaker-make.include``. This file is supplied
with ``beaker-devel`` as seen below.

::

    [root@dhcp83-5 example-compilation]# cat /usr/share/rhts/lib/rhts-make.include
    # Copyright (c) 2006  All rights reserved. This copyrighted material l
    # is made available to anyone wishing to use, modify, copy, or
    # redistribute it subject to the terms and conditions of the GNU General
    # Public License v.2.
    #
    # This program is distributed in the hope that it will be useful, but WITHOUT AN Y
    # WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
    # PARTICULAR PURPOSE. See the GNU General Public License for more details.
    #
    # You should have received a copy of the GNU General Public License
    # along with this program; if not, write to the Free Software
    # Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
    #
    # Author: Your Name <name@company.com>

    #
    # rhts-make.include
    #
    # default rules and settings for rhts makefiles
    #

    # Common Variables.
    TEST_DIR=/mnt/tests$(TEST)
    INSTALL_DIR=$(DEST)$(TEST_DIR)
    METADATA=testinfo.desc

    # tag: mark the test source as a release

    tag:
            rhts-mk-tag-release

    release: tag

    # prep: prepare the test(s) for packaging

    install: $(FILES) runtest.sh testinfo.desc
            mkdir -p $(INSTALL_DIR)
            cp -a $(FILES) Makefile $(INSTALL_DIR)
            install -m 0755 runtest.sh $(INSTALL_DIR)

    # package: build the test package

    package:
            rhts-mk-build-package


    # submit: submit the test package to RHTS

    submit:
            rhts-mk-build-package -s $(TESTSERVER)

    ##################################################
    # example makefile
    #
    # include ~/devel/rhts/greg/rhts_nb/make.include
    #
    # FILES=prog1.c prog2.c
    #
    # ARENA=$(DEST)/mnt/tests/glibc/double-free-exploit
    #
    # install:
    #       mkdir -p $(ARENA)
    #       cp -a runtest.sh $(FILES) $(ARENA)
    #
    # run: tests
    #       runtest.sh
    #
    # tests: prog2 prog2

The ``tag`` target is used to tag a package in anticipation of
submitting it to a test lab.

The submit target is used to submit a package to a test lab and requires
the ``TESTSERVER`` variable to be defined. It builds an RPM of the test
(if necessary) and uploads the test package to a test lab controller
where it can be used to schedule tests.

``$(METADATA)``
---------------

Following is an example of the ``METADATA`` section needed to execute a
basic test. Following subsections will comment briefly on the values
that must be set manually (not set by variables) and optional values to
enhance test reporting and execution.

::

    $(METADATA): Makefile
        @touch $(METADATA)
        @echo "Owner:        Your Name <name@company.com>" > $(METADATA)
        @echo "Name:         $(TEST)" >> $(METADATA)
        @echo "Path:         $(TEST_DIR)" >> $(METADATA)
        @echo "License:      GPLv2" >> $(METADATA)
        @echo "TestVersion:  $(TESTVERSION)" >> $(METADATA)
        @echo "Description:  Ensure that compiling a simple .c file works as expected" >> $(METADATA)
        @echo "TestTime:     1m" >> $(METADATA)
        @echo "RunFor:       $(PACKAGE_NAME)" >> $(METADATA)  # add any other packages for which your test ought to run here
        @echo "Requires:     $(PACKAGE_NAME)" >> $(METADATA)  # add any other requirements for the script to run here

Owner
-----

Owner: (optional) is the person responsible for this test. Initially for
Beaker, this will be whoever committed the test to Subversion. A naming
policy may have to be introduced as the project develops. Acceptable
values are a subset of the set of valid email addresses, requiring the
form: "Owner: human readable name <username@domain>".

Name
----

``Name``:(required) It is assumed that any result-reporting framework
will organize all available tests into a hierarchical namespace, using
forward-slashes to separate names (analogous to a path). This field
specifies the namespace where the test will appear in the framework, and
serves as a unique ID for the test. Tests should be grouped logically by
the package under test. This name should be consistent with the name
used in source control too. Since some implementations will want to use
the file system to store results, make sure to only use characters that
are usable within a file system path.

Description
-----------

``Description``\ (required) must contain exactly one string.

For example:

::

    Description: This test tries to map five 1-gigabyte files with a single process.
    Description: This test tries to exploit the recent security issue for large pix map files.
    Description: This test tries to panic the kernel by creating thousands of processes.

TestTime
--------

Every ``Makefile`` must contain exactly one ``TestTime`` value. It
represent the upper limit of time that the ``runtest.sh`` script should
execute before being terminated. That is, the API should automatically
fail the test after this time period has expired. This is to guard
against cases where a test has entered an infinite loop or caused a
system to hang. This field can be used to achieve better test lab
utilization by preventing the test from running on a system
indefinitely.

The value of the field should be a number followed by either the letter
"m" or "h" to express the time in minutes or hours. It can also be
specified it in seconds by giving just a number. It is recommended to
provide a value in minutes, for readability.

The time should be the absolute longest a test is expected to take on
the slowest platform supported, plus a 10% margin of error. It is
usually meaningless to have a test time of less than a minute, since
some implementations of the API may be attempting to communicate with a
busy server such as writing back to an NFS share or performing an
XML-RPC call.

For example:

::

    TestTime: 90   # 90 seconds
    TestTime: 1m   # 1 minute
    TestTime: 2h   # 2 hours

Requires
--------

``Requires`` one or more. This field indicates the packages that are
required to be installed on the test machine for the test to work. The
package being tested is automatically included via the ``PACKAGE_NAME``
variable. Anything ``runtest.sh`` needs for execution must be included
here.

This field can occur multiple times within the metadata. Each value
should be a space-separated list of package names, or of Kickstart
package group names preceded with an @ sign. Each package or group must
occur within the distribution tree under test (specifically, it must
appear in the ``comps.xml`` file).

For example:

::

    @echo "Requires:     gdb" >> $(METADATA) 
    @echo "Requires:     @legacy-software-development" >> $(METADATA) 
    @echo "Requires:     @kde-software-development" >> $(METADATA) 
    @echo "Requires:     -pdksh" >> $(METADATA)

The last example above shows that we don't want a particular package
installed for this test. Normally you shouldn't have to do this unless
the package is installed by default.

In a lab implementation, the dependencies of the packages listed can be
automatically loaded using yum.

Note that unlike an RPM spec file, the names of packages are used rather
than Provides: dependencies. If one of the dependencies changes name
between releases, one of these approaches below may be helpful:

-  for major changes, split the test, so that each release is a separate
   test in a sub-directory, with the common files built from a shared
   directory in the ``Makefile``.

-  if only a dependency has changed name, specify the union of the names
   of dependencies in the Requires: field; an implementation should
   silently ignore unsolvable dependencies.

-  it may be possible to work around the differences by logic in the
   section of the ``Makefile`` that generates the ``testinfo.desc``
   file.

When writing a multihost test involving multiple roles client(s) and
server(s), the union of the requirements for all of the roles must be
listed here.

RhtsRequires
------------

``RhtsRequires`` one or more. This field indicates the other beaker
tests that are required to be installed on the test machine for the test
to work.

This field can occur multiple times within the metadata. Each value
should be a space-separated list of its task name enclosed in test().
Each task must exist on the Beaker Scheduler.

For example:

::

    @echo "RhtsRequires:     test(/distribution/rhts/common)" >> $(METADATA)

RunFor
------

``RunFor`` allows for the specification of the packages which are
relevant for the test. This field is the hook to be used for locating
tests by package. For example, when running all tests relating to a
particular package[1], an implementation should use this field.
Similarly, when looking for results on a particular package, this is the
field that should be used to locate the relevant test runs.

When testing a specific package, that package must be listed in this
field. If the test might reasonably be affected by changes to another
package, the other package should be listed here. If a package changes
name in the various releases of the distribution, all its names should
be listed here.

This field is optional; and can occur multiple times within the
metadata. The value should be a space-separated list of package names.

.. _testinfo-releases:

Releases
--------

Some tests are only applicable to certain distribution releases. For
example, a kernel bug may only be applicable to RHEL3 which contains the
2.4 kernel. Limiting the release should only be used when a test will
not execute on a particular release. Otherwise, the release should not
be restricted so that your test can run on as many different releases as
possible.

-  Valid ``Releases`` are anything that is a valid Family in Beaker,
   such as:

   -  RedHatEnterpriseLinux3

   -  RedHatEnterpriseLinux4

   -  RedHatEnterpriseLinuxServer5

   -  RedHatEnterpriseLinuxClient5

   -  FedoraCore6

   -  Fedora7

   -  Fedora8

-  Releases can be used in two ways:

   -  specifying releases you *want* run your test for : For example, if
      you want to run your test on RHEL3 and RHEL4 only, add "Releases:
      RedHatEnterpriseLinux3 RedHatEnterpriseLinux4" to your Makefile
      METADATA variable, i.e.:

      ::

          ...
          @echo "Requires:        openldap-servers" >> $(METADATA)
          @echo "Releases:        RedHatEnterpriseLinux3 RedHatEnterpriseLinux4" >> $(METADATA)
          @echo "Priority:        Normal" >> $(METADATA)
          ...

   -  specifying releases you *don't want* run your test for (using "-"
      sign before given releases): For example, if you don't want to run
      your test on RHEL3, but the other releases are valid for your
      test, add "Releases: -RedHatEnterpriseLinux3" to your Makefile
      METADATA variable, i.e.:

      ::

          ...
          @echo "Requires:        openldap-servers" >> $(METADATA)
          @echo "Releases:        -RedHatEnterpriseLinux3" >> $(METADATA)
          @echo "Priority:        Normal" >> $(METADATA)
          ...
