An example task: checking for ext4 support
==========================================

To get a basic idea of how we can use :program:`beaker-wizard`, we will create a
new task which will check whether the platform supports the ext4 filesystem. We use
`restraint <https://restraint.readthedocs.org/en/latest/>`_ as a test harness,
since it allows us to define Beaker jobs with tasks retrieved from a git
repository.

If you have a basic understanding of test frameworks and don't want to install
the :program:`beaker-wizard`, you can jump right to the
:ref:`writing-example-task-implementation` part of the tutorial.

Prerequisites
-------------

The :ref:`beaker-wizard <beaker-wizard>` utility provides a guided step by
step method to create a task without the need to manually create all of the
necessary files.

In case you do not have :program:`beaker-wizard` available, install it by
following the installation guide for the :ref:`bkr client
<installing-bkr-client>`.

Generating the skeleton using beaker-wizard
-------------------------------------------

Create a directory with the name ``ext4-task``. The directory will hold metadata
and task executable. From your terminal, type::

     $ mkdir ext4-task
     $ cd ext4-task
     $ beaker-wizard --current-directory

and follow :program:`beaker-wizard`. If in doubt choose the default values offered by the
wizard. As a **test-name** use ``ext4-test``. Finally, press the enter key to
create the task::

    File PURPOSE written
    File runtest.sh written
    File Makefile written


.. _writing-example-task-implementation:

Implementing the test
---------------------

In the ``ext4-test`` directory, you will notice that the three files:
``PURPOSE``, ``runtest.sh``, and a ``Makefile`` have been created. The test
itself is kept in ``runtest.sh`` executed by the test harness using the
``Makefile``, while ``PURPOSE`` provides information for humans.

``PURPOSE`` and ``Makefile`` are actually not needed when using the
:program:`restraint` test harness. Alternatively, you can create a
`metadata <https://restraint.readthedocs.org/en/latest/tasks.html#metadata>`_
file instead.

The test is written using `BeakerLib
<https://github.com/beakerlib/beakerlib/wiki/man>`_ commands. The functionality is
divided into three stages: setup, start and cleanup, as indicated by the
``rlPhaseStartSetup``, ``rlPhaseStartTest`` and ``rlPhaseStartCleanup``
functions respectively.

Remove the setup (``rlPhaseStartSetup``) and teardown
(``rlPhaseStartCleanup``) phases, since they're not needed for this simple
test. Replace the actual test code (starting with ``rlPhaseStartTest``) so that
the file looks like this:

.. code-block:: bash

    #!/bin/bash
    # Include Beaker environment
    . /usr/bin/rhts-environment.sh || exit 1
    . /usr/share/beakerlib/beakerlib.sh || exit 1

    rlJournalStart
        rlPhaseStartTest
            rlRun "cat /proc/filesystems | grep 'ext4'" 0 "Check if ext4 is supported"
        rlPhaseEnd
    rlJournalPrintText
    rlJournalEnd

The `BeakerLib manual <https://github.com/beakerlib/beakerlib/wiki/man>`_
provides an extensive reference of what utility functions are available to test
authors.

Testing the task from a git repository
--------------------------------------

In order to test your task, create a public git repository (e.g. Fedora's
`Pagure <https://pagure.io/>`_, `github <https://www.github.com>`_, etc) and
publish your code.

Next we will submit a Beaker job to run our newly published task. We will need
to write a job definition using Beaker's :ref:`job XML<job-xml>` syntax. As
mentioned above, we want to select the :program:`restraint` harness which is
capable of fetching our task directly from its git repository. The job will
contain one recipe, using a version of Fedora, with one task in the
recipe:

.. code-block:: xml
   :linenos:

    <job>
      <whiteboard>
        ext4 test
      </whiteboard>
      <recipeSet>
        <recipe ks_meta="harness='restraint beakerlib'">
          <distroRequires>
              <distro_family op="=" value="Fedora23"/>
              <distro_arch op="=" value="x86_64"/>
          </distroRequires>
          <hostRequires />

          <task>
            <fetch url="<URL OF YOUR TASK REPOSITORY>" />
          </task>

        </recipe>
      </recipeSet>
    </job>

Running the task
----------------

You can then submit the job (see :ref:`job-submission`). After the job has
completed, you can access the logs as described in :ref:`job-results`. You will
see that on success, the ``taskout.log`` file will provide verbose information
about the progress of the test and it's result.

The overall workflow of creating a task for a test, submitting a job to
run the test and accessing the test results is illustrated in
:ref:`chronological-overview`.

.. _writing-example-task-references:

Next steps
----------

The Beaker `meta tasks git repository
<https://github.com/beaker-project/beaker-meta-tasks/tree/master/>`_ provides tasks
which are in use daily by the Beaker team. They can give you further information
on how you can write tasks. The task described in this tutorial can be inspected
in the same repository under `examples
<https://github.com/beaker-project/beaker-meta-tasks/tree/master/examples/>`_. If you
run into problems when scheduling your task in Beaker, the
:ref:`troubleshooting` section might be of interest to you. Further information
on the test harness used in this tutorial can be found in the `Restraint
<https://restraint.readthedocs.org/en/latest/>`_ documentation.
