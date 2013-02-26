Tasks
-----

Tasks are the lowest unit in the Job hierarchy, and running a Task is
the primary purpose of running a Job. There purpose is to run one or
more commands, and then collect the results of those commands in a way
that other entities can access them. You can run as many or as few Tasks
in a Job as you like.

Creating a task
~~~~~~~~~~~~~~~

A Beaker task consists of three primary files: ``PURPOSE``,
``runtest.sh`` and a ``Makefile``. There can be other files as needed
for the task. ``PURPOSE`` is a text file that describes the task in some
detail. There is no restriction on the length of the description. The
core of each Beaker task is the ``runtest.sh`` shell script. It performs
the testing (or delegates the work by invoking another script or
executable) and reports the results. You may either write all the code
that performs the test in the ``runtest.sh`` script or, when
appropriate, call an external executable that does the bulk of the work.
This external executable can be in any other language as long as it is
appropriately executed from the ``runtest.sh`` script. This script uses
``BeakerLib`` functions to setup, start, stop and cleanup after the task
has been run. Once you have written your test in this script, you can
either run it locally (when appropriate) or package it as an RPM package
and upload it to Beaker. The ``Makefile`` defines targets to carry out
these and other related functions.

The ``beaker-wizard`` utility provides a guided step by step method to
create a task without the need to manually create the above files. To
get a basic idea of how we can use beaker-wizard, we will create a new
task which will check the support for the ext4 filesystem. If you have
the beaker-client package installed, you should already have
``beaker-wizard`` available. You will also need to install the
rhts-devel package. Create a new directory, where we will create the
task. In most cases, your task will be meant to test a particular
package. Hence, you should create a directory with the package name if
that's the case. In this case, we will simply create a directory with
the name ``mytask``. From your terminal, type::

     $ mkdir mytask
     $ cd mytask
     $ beaker-wizard

You will see a welcome message as follows::

    Welcome to The Beaker Wizard!
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    It seems, you're running the beaker-wizard for the first time.
    I'll try to be a little bit more verbose. Should you need
    any help in the future, just try using the "?" character.


    Bugs or CVE's related to the test
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Supply one or more bug or CVE numbers (e.g. 123456 or 2009-7890). Use
    the '+' sign to add the bugs instead of replacing the current list.
    [None?] 

If you are writing this task to write a test related to a specific bug,
enter the bug number here. In our case, we are not, so simply press the
return key. The wizard will then proceed to ask you several questions
regarding the test such as the description, the type of test, and
others. The wizard gives you choices for the answer wherever relevant,
but also has a default answer when one is not provided. Either enter
your own option or press return to accept the default answer::

    Test name
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Use few, well chosen words describing what the test does. Special
    chars will be automatically converted to dashes.
    [a-few-descriptive-words?] ext4-test

    What is the type of test?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Possible values: Regression, Performance, Stress, Certification,
    Security, Durations, Interoperability, Standardscompliance,
    Customeracceptance, Releasecriterium, Crasher, Tier1, Tier2, Alpha,
    KernelTier1, KernelTier2, Multihost, MultihostDriver, Install,
    FedoraTier1, FedoraTier2, KernelRTTier1, KernelReporting, Sanity
    Test type must be exactly one from the list above.
    [Sanity?] 

    Namespace
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Possible values: distribution, installation, kernel, desktop, tools,
    CoreOS, cluster, rhn, examples, performance, ISV, virt
    Provide a root namespace for the test.
    [CoreOS?] installation

    Short description
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Provide a short sentence describing the test.
    [What the test does?] Check whether ext4 filesystem is supported out of the box

    Time for test to run
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    The time must be in format [1-99][m|h|d] for 1-99 minutes/hours/days
    (e.g. 3m, 2h, 1d)
    [5m?] 

    Author's name
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Put your name [middle name] and surname here, abbreviations allowed.
    [Your Name?] Task Author

    Author's email
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Email address in lower case letters, dots and dashes. Underscore
    allowed before the "@" only.
    [user@hostname.com?] tauthor@example.com

    Ready to create the test, please review
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    /installation/mytask/Sanity/ext4-test

                 Namespace : installation
                   Package : mytask
                 Test type : Sanity
             Relative path : None
                 Test name : ext4-test
               Description : Check whether ext4 filesystem is supported out of the box

        Bug or CVE numbers : None
      Prefix the test name : Yes
      Reproducers to fetch : None

          Run for packages : mytask
         Required packages : mytask
             Architectures : All
                  Releases : All
                   Version : 1.0
                      Time : 5m

                  Priority : Normal
                   License : GPLv2
              Confidential : No
               Destructive : No

                  Skeleton : beakerlib
                    Author : Task Author
                     Email : tauthor@example.com

    Type a few letters from field name to edit or press ENTER to confirm.
    Use the "write" keyword to save current settings as preferences.
    [Everything OK?] 

Once you have answered all the questions, the wizard allows you to
review the answers you have. As you can see, beaker-wizard assumed
default values for some of the options such as ``Run for packages``,
``Required packages``, ``License`` and others without asking from you.
As per the instructions above, you can edit any of these or the ones you
specified earlier before creating the test. For example, if this test is
Confidential, you can change it, like so::

    [Everything OK?] Confi

    Confidential
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Possible values: Yes, No
    [No?] Yes

    Ready to create the test, please review
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ..
    ..

Once you have changed the value of Confidential, you will again be able
to review all the options (and change if necessary). Finally, when you
are satisfied, press the enter key to create the test::

    Directory Sanity/ext4-test created
    File Sanity/ext4-test/PURPOSE written
    File Sanity/ext4-test/runtest.sh written
    File Sanity/ext4-test/Makefile written

In the Sanity/ext4-test directory, you will notice that the three files:
``PURPOSE``, ``runtest.sh`` and a ``Makefile`` have been created. You
will see that ``PURPOSE`` will have the test description you entered
earlier along with the author's details. The ``runtest.sh`` file will
have the following contents::

    #!/bin/bash
    # vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #   runtest.sh of /installation/mytask/Sanity/ext4-test
    #   Description: Check whether ext4 filesystem is supported out of the box
    #   Author: Task Author <tauthor@example.com>
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
    #
    #   This copyrighted material is made available to anyone wishing
    #   to use, modify, copy, or redistribute it subject to the terms
    #   and conditions of the GNU General Public License version 2.
    #
    #   This program is distributed in the hope that it will be
    #   useful, but WITHOUT ANY WARRANTY; without even the implied
    #   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
    #   PURPOSE. See the GNU General Public License for more details.
    #
    #   You should have received a copy of the GNU General Public
    #   License along with this program; if not, write to the Free
    #   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    #   Boston, MA 02110-1301, USA.
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Include Beaker environment
    . /usr/bin/rhts-environment.sh || exit 1 
    . /usr/share/beakerlib/beakerlib.sh || exit 1 

    PACKAGE="mytask" 

    rlJournalStart
        rlPhaseStartSetup
            rlAssertRpm $PACKAGE
            rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
            rlRun "pushd $TmpDir"
        rlPhaseEnd

        rlPhaseStartTest
            rlRun "touch foo" 0 "Creating the foo test file"
            rlAssertExists "foo"
            rlRun "ls -l foo" 0 "Listing the foo test file"
        rlPhaseEnd

        rlPhaseStartCleanup
            rlRun "popd"
            rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
        rlPhaseEnd
    rlJournalPrintText
    rlJournalEnd

The GPLv2 license header in the beginning is default for a task. You can
change the license to something more appropriate for your needs during
the task creation. ``beaker-wizard`` will try to find a license header
corresponding to the specified license and if it is not present will
insert a default text where you can insert the appropriate header
information and copyright notice. Please consult the ``beaker-wizard``
man page for details on how you can add your own license text using a
preference file.

The package for which this task is defined is declared in the
``PACKAGE`` variable. We will simply delete this line since this task is
not for testing a package. Every beaker test must begin with
``rlJournalStart``. This initializes the journaling functionality so
that the logging mechanism is initialized so that your test results can
be saved. The functionality of a test is divided into three stages:
setup, start and cleanup indicated by the ``rlPhaseStartSetup``,
``rlPhaseStartTest`` and ``rlPhaseStartCleanup`` functions respectively.
The setup phase first checks if the package which we want to test is
available and then creates a temporary directory and moves there so that
all the test activities are performed in that directory. The
``rlPhaseStartTest`` and its corresponding ``rlPhaseEnd``, encloses the
core test logic. Here, as you can see, the test is checking whether an
empty file has been created successfully or not. We will replace these
lines to include our own logic to check for the presence of ext4
support. The cleanup phase is used to cleanup the working directory
created for the test and change back to the original working directory.
For our task, we don't need this. The modified ``runtest.sh`` file looks
like::

    #!/bin/bash
    # vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #   runtest.sh of /installation/mytask/Sanity/ext4-test
    #   Description: Check whether ext4 filesystem is supported out of the box
    #   Author: Task Author <tauthor@example.com>
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
    #
    #   This copyrighted material is made available to anyone wishing
    #   to use, modify, copy, or redistribute it subject to the terms
    #   and conditions of the GNU General Public License version 2.
    #
    #   This program is distributed in the hope that it will be
    #   useful, but WITHOUT ANY WARRANTY; without even the implied
    #   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
    #   PURPOSE. See the GNU General Public License for more details.
    #
    #   You should have received a copy of the GNU General Public
    #   License along with this program; if not, write to the Free
    #   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
    #   Boston, MA 02110-1301, USA.
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Include Beaker environment
    . /usr/bin/rhts-environment.sh || exit 1
    . /usr/share/beakerlib/beakerlib.sh || exit 1

    rlJournalStart
        rlPhaseStartTest
            rlRun "cat /proc/filesystems | grep 'ext4'" 0 "Check if ext4 is supported"
        rlPhaseEnd
    rlJournalPrintText
    rlJournalEnd

You can now run this test locally to see if everything is correctly
working using ``make run``::

    # make run
    test -x runtest.sh || chmod a+x runtest.sh
    ./runtest.sh

    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    :: [   LOG    ] :: Test
    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

            ext4
    :: [   PASS   ] :: Check if ext4 is supported

    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    :: [   LOG    ] :: TEST PROTOCOL
    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    :: [   LOG    ] :: Test run ID   : oCNr6jM
    :: [   LOG    ] :: Package       : unknown
    :: [   LOG    ] :: Test started  : 2012-11-07 02:58:07 EST
    :: [   LOG    ] :: Test finished : 2012-11-07 02:58:07 EST
    :: [   LOG    ] :: Test name     : /installation/mytask/Sanity/ext4-test
    :: [   LOG    ] :: Distro:       : Red Hat Enterprise Linux Server release 6.3 (Santiago)
    :: [   LOG    ] :: Hostname      : hostname.example.com
    :: [   LOG    ] :: Architecture  : x86_64

    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    :: [   LOG    ] :: Test description
    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    PURPOSE of /installation/mytask/Sanity/ext4-test
    Description: Check whether ext4 filesystem is supported out of the box
    Author: Task Author <tauthor@example.com>


    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    :: [   LOG    ] :: Test
    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    :: [   PASS   ] :: Check if ext4 is supported
    :: [   LOG    ] :: Duration: 0s
    :: [   LOG    ] :: Assertions: 1 good, 0 bad
    :: [   PASS   ] :: RESULT: Test

    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    :: [   LOG    ] :: /installation/mytask/Sanity/ext4-test
    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

    :: [   LOG    ] :: Phases: 1 good, 0 bad
    :: [   PASS   ] :: RESULT: /installation/mytask/Sanity/ext4-test
    :: [02:58:07] ::  JOURNAL XML: /tmp/beakerlib-oCNr6jM/journal.xml
    :: [02:58:07] ::  JOURNAL TXT: /tmp/beakerlib-oCNr6jM/journal.txt

As you can see, the test passes with the logs saved in the above files.
Before we can upload this task to Beaker, we will have to package this
is an RPM. Both these steps can be accomplished via ``make bkradd``
(assuming you have set your beaker client configuration successfully).
If you do not see any errors here, then you should see that this task
has been uploaded to the task library *http://your-beaker-root/tasks/*.

To learn more about the functions used to write the test, please see the
`BeakerLib documentation 
<https://fedorahosted.org/beakerlib/wiki/Manual>`_. You can learn
more about ``beaker-wizard`` from its
:ref:`man page <beaker-wizard>`.

Running the task
~~~~~~~~~~~~~~~~

Once the task is available in the "Task Library", you have to write a
job description (XML file) to run this test on a system provisioned in
Beaker. A sample job description that runs this task would be as
follows::

    <job>
      <whiteboard>
        ext4 test
      </whiteboard>
      <recipeSet>
        <recipe>

          <distroRequires>
            <distro_arch op="=" value="x86_64" />
          </distroRequires>

          <hostRequires>
            <system_type value="Machine"/>
          </hostRequires>

          <task name="/installation/mytask/Sanity/ext4-test" role="STANDALONE"/>

        </recipe>
      </recipeSet>
    </job>

You can then :ref:`submit the job <job-submission>`. After the job 
has completed, you can access the logs as described in :ref:`job-results`.
You will see that on success, the ``TESTOUT.log``
file will contain the same log as when it was run locally. You can also obtain 
the logs using the :manpage:`bkr job-logs <bkr-job-logs(1)>` command. In some 
cases, in addition to the log files you may also want to retrieve some files 
from the test system. For example, in this case you may want to examine the 
contents of ``/proc/filesystems`` on the system that run the test. This can be 
done using the Beakerlib function ``rlFileSubmit``.

The overall workflow of creating a task for a test, submitting a job to
run the test and accessing the test results are illustrated in 
:ref:`chronological-overview`.

Updating a task
~~~~~~~~~~~~~~~

To upload newer versions of your task, you will need to update the
``VERSION`` variable in your ``Makefile``, else Beaker will not add it
saying that its already present in the task library.

.. admonition:: Version Control for your Tests

   If you plan to work on revisions of your test in future, it is a good idea 
   to initialize a repository in your task directory (i.e. ``mytask`` in this 
   case). If you are using git, for example, you can create a tag for your task 
   using ``make tag`` and ``make bkradd`` will automatically use the most 
   recent tag for adding versioning information to your task and hence you 
   don't have to change the ``VERSION`` variable in the ``Makefile`` yourself.

Makefile
~~~~~~~~

As you have seen so far, we have used the ``Makefile`` to run a test
locally and also building and uploading the RPM to Beaker. See :ref:`makefile`.

.. _task-searching:

Task searching
~~~~~~~~~~~~~~

To search for a Task, go to "Scheduler>Task" Library at the top of the
page. The default search is on the "Name" property, with the "contains"
operator. See :ref:`system-searching` for
further details.

Once you've found a particular Task, you can see its details by clicking
on the Link in the "Name" column.

It's also possible to search on the history of the running of Tasks.
This is made possible by the "Executed Tasks" search, which is accessed
by clicking on a task.

.. _adding-tasks:

Adding a new task
~~~~~~~~~~~~~~~~~

If you already have a task packaged as an RPM, click "Scheduler>New
Task" from the main menu bar. You will need to click on "Browse" to
locate your task, and then add it with the "Submit Data" button. See
:manpage:`bkr task-add <bkr-task-add(1)>` for how to do this via the
beaker client.

If you are trying to update an existing task, the version of the new
task RPM will need to be higher. This can be achieved by running
``make tag`` (if in a local checkout of a git or CVS repo), or manually
adjusting the ``TESTVERSION`` in the task's ``Makefile`` (see
:ref:`makefile-testversion`).
