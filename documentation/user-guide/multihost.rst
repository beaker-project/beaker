.. _multihost-tasks:

Multihost tasks
===============

Feature Requirements
--------------------
The multihost feature is brought to you by Beaker and the
test harness (e.g. Restraint).  Multihosting is mostly performed on
the test harness itself. This section provides an overview
of how multihost works with the currently supported test harness.
If your test harness does not support task synchronization,
then this section can be ignored.  If you are using only
the test harness and not beaker, this section describes
a work-around.

Introduction
------------
Beaker has support for tasks that run on multiple hosts to test the
interactions of a client and a server. When a multihost task is run in the lab,
one or more machines will be allocated to each role in the test. Each machine
has its own recipe and these recipes are defined within a recipeset in a
single job.

Each machine under test may want to synchronize to ensure that they
start the test together, and may need to synchronize at various stages
within the test. While Beaker doesn't assign any particular semantics to
role names (it just uses them to set the corresponding task environment
variables), there are three common roles used in many multi-host
tests: client, server and driver.

For many purposes, all you will need are client and server roles. For a
test involving one or more clients talking to one or more servers, a
typical approach would be for the clients to block while the servers
get ready. Once all servers are ready, the clients perform the
testing they need using the services provided by the server machines.
The servers block waiting for clients to finish while in parallel
carrying out work requested by the clients.  In conclusion, the clients
eventually report results back to the test.  Once all clients have
finished testing, the server tests unblock and report their results.

Each participant in a test will report results within the same
job and report to different places within the result hierarchy.
For example, the server part of the test may PASS if it survives the
load, but the client part might FAIL upon, say, getting erroneous data
from the server; this would lead to an overall FAIL for the test.

If you have a more complex arrangement, it is possible to have a driver
machine which controls all of the testing.

All of the participants in a multihost test share a single
``runtest.sh``, which performs every role within the test (e.g. the
client role and server role). When a multihost test is run in the lab,
the framework automatically sets environment variables to allow the
various participants to know what their role should be, which other
machines they should be talking to, and what roles those other machines
are performing in the test. You will need to have logic in your
``runtest.sh`` to examine the role variables and perform the necessary
role accordingly.

You can choose to perform your own synchronization or have the harness
(e.g. restraint) perform task synchronization for you.  If you want the
harness to perform synchronization, the role=SERVERS and role=CLIENTS are
required in your job recipes/tasks.  The harness performs synchronization of
servers and clients at the completion of the task. The tasks will
all block at the end until the last one has finished.  They will then
move onto the next task but not in unison since some may be
sleeping before rechecking the status of others.

Environment Variables for Synchronization
-----------------------------------------
The following environment variables are shared by all instances of the
runtest.sh within a recipeset for harness controlled synchronization.
If you choose different role names than CLIENTS/SERVERS, your tasks are
responsible for synchronization actions as described later.  However,
the harness with beaker's help, will still export role enviroment variables
with your chosen names and wlll separate FQDNs with a space.

.. envvar:: CLIENTS

   Contains a space-separated list of FQDNs of clients within this
   recipeset (that is, systems running recipes marked with the ``CLIENTS``
   role in the job XML).

.. envvar:: SERVERS

   Contains a space-separated list of FQDNs of servers within this
   recipeset (that is, systems running recipes marked with the ``SERVERS``
   role in the job XML).

.. envvar:: DRIVER

   Contains the FQDN for the driver of this recipe set, if any (that is, a
   system running a recipe marked with the ``DRIVER`` role in the job XML).

When writing your own synchronization, you can use the variable :envvar:`HOSTNAME`
in your ``runtest.sh`` to determine its identity. :envvar:`HOSTNAME` is set by
the harness task environment plugin, and is unique for each host within
a recipeset.  Your test can use :envvar:`HOSTNAME` to search the client, server,
or driver environment variables to determine its role.  An example of this is
shown later in :ref:`sync-handling-env-vars`.

When you are developing your test outside the lab environment, only
:envvar:`HOSTNAME` is set for you (when sourcing the
``rhts-environment.sh`` script). One way to run multihost tests outside a
Beaker instance is to copy the test to multiple development machines, set
up :envvar:`CLIENTS`, :envvar:`SERVERS`, and :envvar:`DRIVER` manually
within a shell on each machine, and then manually run the ``runtest.sh``
on each one, debugging as necessary. Alternatively, support for standalone
testing may be added directly to the test script, as described in
:ref:`multihost-standalone`.

Simple job.xml for Synchronization
----------------------------------
In its simplest form, a job with multihost testing may look something like::

    <job>
      <RecipeSet>
         <recipe role='MYSERVERS'>
            <task name='/distribution/check-install'/>
            <task name='/my/multihost/test'/>
         </recipe>
         <recipe role='MYCLIENTS'>
            <task name='/distribution/check-install'/>
            <task name='/my/multihost/test'/>
         </recipe>
      </RecipeSet>
    </job>

.. note:: For brevity some necessary parts are left out in the above job
   definition. See :ref:`job-xml` for details.

As there is only one recipe in the recipe set with each defined role,
submitting the job above will export environmental variables
:envvar:`MYSERVERS` and :envvar:`MYCLIENTS` set to their respective
FQDNs.

If you replace the roles with SERVERS/CLIENTS, the harness
will perform synchronization operations for you.  In this case,
roles MYSERVERS/MYCLIENTS are used instead to begin showing you how to
perform synchronization on your own without harness end-of-task
synchronization.

Any multihost testing must ensure that the task execution order aligns
correctly on all machines. This includes synchronization controlled by
the harness. For example, the below will fail:

::

              <recipe>
                <task role='STANDALONE' name='/distribution/check-install'/>
                <task role='STANDALONE' name='/my/test/number1'/>
                <task role='MYSERVERS'  name='/my/multihost/test'/>
              </recipe>
              <recipe>
                <task role='STANDALONE' name='/distribution/check-install'/>
                <task role='MYCLIENTS'  name='/my/multihost/test'/>
              </recipe>

This will fail because the multihost test is the third test on the server
side and it's the second test on the client side. To fix this, you can pad
in dummy test cases on the side that has fewer test cases. There is a
dummy test that lives in /distribution/utils/dummy for this purpose. So,
the above can be fixed as:

::

              <recipe>
               <task role='STANDALONE' name='/distribution/check-install'/>
               <task role='STANDALONE' name='/my/test/number1'/>
               <task role='MYSERVERS'  name='/my/multihost/test'/>
              </recipe>
              <recipe>
               <task role='STANDALONE' name='/distribution/check-install'/>
               <task role='STANDALONE' name='/distribution/utils/dummy'/>
               <task role='MYCLIENTS'  name='/my/multihost/test'/>
              </recipe>

.. _sync-handling-env-vars:

Handling Environment Variables in your synchronized ``runtest.sh``
------------------------------------------------------------------
In the sample job.xml provided previously, the ``runtest.sh`` in
``/my/multihost/test`` test might look like::

    Server() {
        # .. server code here
    }

    Client() {
        # .. client code here
    }

    if test -z "$JOBID" ; then
        echo "Variable jobid not set! Assume developer mode"
        MYSERVERS="test1.example.com"
        MYCLIENTS="test2.example.com"
        DEVMODE=true
    fi

    if [ -z "$MYSERVERS" -o -z "$MYCLIENTS" ]; then
        echo "Can not determine test type! Client/Server Failed:"
        RESULT=FAILED
        report_result $TEST $RESULT
    fi

    if $(echo $MYSERVERS | grep -q $:envvar:`HOSTNAME`); then
        TEST="$TEST/Server"
        Server
    fi

    if $(echo $MYCLIENTS | grep -q $:envvar:`HOSTNAME`); then
        TEST="$TEST/Client"
        Client
    fi

We have ``Server()`` and ``Client()`` functions which will be executed
by recipes with the :envvar:`MYSERVERS` and :envvar:`MYCLIENTS` role
respectively.

Then we test for :envvar:`JOBID` which indicates if the script is
running inside a Beaker instance; otherwise, it's being run on the
test developer's local workstation or any other non-Beaker system.

The tests comparing :envvar:`MYSERVERS` and :envvar:`MYCLIENTS` to
:envvar:`HOSTNAME` determine what code to run on this particular
machine. As mentioned before, since only one recipe in our
recipe set uses each role, the :envvar:`MYSERVERS` and :envvar:`MYCLIENTS`
environmental variables will be set to their respective machines' names
and exported on both machines.

Writing User-Defined Synchronization in your ``runtest.sh``
-----------------------------------------------------------
For most meaningful multi-host tests, there has to be some sort of
coordination and synchronization between the machines and the execution
of the test code on both sides. While in some cases, this may be handled
by a dedicated recipe with the :envvar:`MYDRIVER` role, the restraint
harness offers two utilities for this purpose:
`rstrnt-sync-set` and `rstrnt-sync-block`.

The `rstrnt-sync-set` command is used to set a state on a machine.
The `rstrnt-sync-block` command is used to block the execution of the
task until a certain state on certain machine(s) is reached. Those familiar
with parallel programming can think of this as a barrier operation.
A brief overview of the usage of these utilities follows:

*  :program:`rstrnt-sync-set`: This command sets the state of the current
   machine to an arbitrary text string.

   Syntax: ``rstrnt-sync-set -s STATE``

*  :program:`rstrnt-sync-block`: This command blocks execution and doesn't
   return until the specified ``STATE`` is set on the specified machine(s).

   Syntax:
   ``rstrnt-sync-block -s STATE [-s STATE1 -s STATE2] machine1 machine2 ...``

For details on the options provided by the restraint harness, refer to
`Restraint Command documentation <https://restraint.readthedocs.io/en/latest/commands.html>`__
and search for these commands.

The role related environment variables are useful here as they contain
the hostnames of all recipes in the recipeset with that role. For example,
you can wait for all recipes with the :envvar:`MYSERVERS` role to set their
state to ``"READY"`` by running::

    rstrnt-sync-block -s READY $MYSERVERS

By default the :program:`rstrnt-sync-block` utility will block until
the local or external watchdog is triggered if the expected state is never
achieved. If this behavior isn't desired, the `--timeout` option can be used
instead. In that case, a zero return code indicates that the desired state
was reached, while a non-zero return code indicates the operation timed out.

These commands require a bit of manual intervention when run in
the standalone execution environment for Beaker task development, as the
Beaker lab controller normally coordinates the barrier operation. See
:ref:`multihost-standalone`.

.. _user-sync-mh-task:

Sample ``runtest.sh`` for a user synchronized multihost task
-------------------------------------------------------------

::

    #!/bin/sh
    # Source the common test script helpers
    . /usr/bin/rhts_environment.sh

    # Save STDOUT and STDERR, and redirect everything to a file.
    exec 5>&1 6>&2
    exec >> "${OUTPUTFILE}" 2>&1

    client()
    {
        echo "-- wait the server to finish."
        rstrnt-sync-block -s "DONE" ${MYSERVERS}

        user="finger1"
        for i in ${MYSERVERS}
        do
            echo "-- finger user \"$user\" from server \"${i}\"."
            ./finger_client "${i}" "${user}"
            # It returns non-zero for failure.
            if [ $? -ne 0 ]; then
                rstrnt-sync-set -s "DONE"
                report_result "${TEST}" "FAIL" 0
                exit 1
            fi
        done

        echo "-- client finishes."
        rstrnt-sync-set -s "DONE"
        result="PASS"
    }

    server()
    {
        # Start server and check it is up and running.
        /sbin/chkconfig finger on && sleep 5
        if ! netstat -a | grep "finger" ; then
            rstrnt-sync-set -s "DONE"
            report_result "${TEST}" "FAIL" 0
            exit 1
        fi
        useradd finger1
        echo "-- server finishes."
        rstrnt-sync-set -s "DONE"
        rstrnt-sync-block -s "DONE" ${MYCLIENTS}
        result="PASS"
    }

    # ---------- Start Test -------------
    result="FAIL"
    if echo "${MYCLIENTS}" | grep "${:envvar:`HOSTNAME`}" >/dev/null; then
        echo "-- run finger test as client."
        TEST=${TEST}/client
        client
    fi
    if echo "${MYSERVERS}" | grep "${:envvar:`HOSTNAME`}" >/dev/null; then
        echo "-- run finger test as server."
        TEST=${TEST}/server
        server
    fi
    echo "--- end of runtest.sh."
    report_result "${TEST}" "${result}" 0
    exit 0

.. _multihost-standalone:

Standalone execution of multihost tests
---------------------------------------

Multihost tests can be more easily executed outside a Beaker instance by
altering their behavior based on the :envvar:`JOBID` variable (or any other
documented variable which is set when running inside a Beaker instance).

For a two machine test that uses the :envvar:`CLIENTS` and
:envvar:`SERVERS` roles, you could create a pair of local virtual machines
and add the following lines at the beginning of your ``runtest.sh`` script::

    # decide if we're running standalone or in a Beaker instance
    if test -z $JOBID ; then
            echo "Variable JOBID not set, assuming standalone"
            CLIENTS="client-vm.example.com"
            SERVERS="server-vm.example.com"
    else
            echo "Variable JOBID set, we're running inside Beaker"
    fi
    echo "Clients: $CLIENTS"
    echo "Servers: $SERVERS"

    # ... rest of test script

