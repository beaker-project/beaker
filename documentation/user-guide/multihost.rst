.. _multihost-tasks:

Multihost tasks
===============

Beaker has support for tasks that run on multiple hosts, e.g. for testing the 
interactions of a client and a server. When a multihost task is run in the lab, 
one or more machines will be allocated to each role in the test. Each machine
has its own recipe.

Each machine under test will need to synchronize to ensure that they
start the test together, and may need to synchronize at various stages
within the test. While Beaker doesn't assign any particular semantics to
role names (it just uses them to set the corresponding task environment
variables), there are three common roles used in used in many multi-host
tests: client, server and driver.

For many purposes all you will need are client and server roles. For a
test involving one or more clients talking to one or more servers, a
typical approach would be for the clients to block whilst the servers
get ready. Once all servers are ready, the clients perform whatever
testing they need, using the services provided by the server machines,
and eventually report results back to the test system. Whilst this is
happening the server tests block; the services running on these machines
are carrying out work for the clients in parallel. Once all clients have
finished testing, the server tests finish, and report their results.

Each participant in a test will be reporting results within the same
job, and so must report to different places within the result hierarchy.
For example, the server part of the test may PASS if it survives the
load, but the client part might FAIL upon, say, getting erroneous data
from the server; this would lead to an overall FAIL for the test.

If you have a more complex arrangement, it is possible to have a driver
machine which controls all of the testing.

All of the participants in a multihost test share a single
``runtest.sh``, which must perform every role within the test (e.g. the
client role and server role). When a multihost test is run in the lab,
the framework automatically sets environment variables to allow the
various participants to know what their role should be, which other
machines they should be talking to, and what roles those other machines
are performing in the test. You will need to have logic in your
``runtest.sh`` to examine these variables, and perform the necessary
role accordingly. These variables are shared by all instances of the
runtest.sh within a recipeset:

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

The variable :envvar:`HOSTNAME` can be used by ``runtest.sh`` to determine its
identity. It is set by ``rhts-environment.sh``, and will be unique for each
host within a recipeset.

Your test can thus decide whether it is a client, server or driver by
investigating these variables: see the example below.

When you are developing your test outside the lab environment, only
:envvar:`HOSTNAME` is set for you (when sourcing the
``rhts-environment.sh`` script). One way to run multihost tests outside a
Beaker instance is to copy the test to multiple development machines, set
up :envvar:`CLIENTS`, :envvar:`SERVERS`, and :envvar:`DRIVER` manually
within a shell on each machine, and then manually run the ``runtest.sh``
on each one, debugging as necessary. Alternatively, support for standalone
testing may be added directly to the test script, as described in
:ref:`multihost-standalone`.

In its simplest form, a job with multihost testing may look something like::

    <job>
      <RecipeSet>
         <recipe role='SERVERS'>
            <task name='/distribution/install'/>
            <task name='/my/multihost/test'/>
         </recipe>
         <recipe role='CLIENTS'>
            <task name='/distribution/install'/>
            <task name='/my/multihost/test'/>
         </recipe>
      </RecipeSet>
    </job>

.. note:: For brevity some necessary parts are left out in the above job
   definition. See :ref:`job-xml` for details.

As there is only one recipe in the recipe set with each defined role,
submitting the job above will export environmental variables
:envvar:`SERVERS` and :envvar:`CLIENTS` set to their respective
FQDNs. This allows a tester to write tests for each machine. So the
``runtest.sh`` in ``/my/multihost/test`` test might look like::

    Server() {
        # .. server code here
    }

    Client() {
        # .. client code here
    }

    if test -z "$JOBID" ; then
        echo "Variable jobid not set! Assume developer mode" 
        SERVERS="test1.example.com"
        CLIENTS="test2.example.com"
        DEVMODE=true
    fi

    if [ -z "$SERVERS" -o -z "$CLIENTS" ]; then
        echo "Can not determine test type! Client/Server Failed:" 
        RESULT=FAILED
        report_result $TEST $RESULT
    fi

    if $(echo $SERVERS | grep -q $:envvar:`HOSTNAME`); then
        TEST="$TEST/Server"
        Server
    fi

    if $(echo $CLIENTS | grep -q $:envvar:`HOSTNAME`); then
        TEST="$TEST/Client"
        Client
    fi

Keep in mind that if you're not fond of writing shell scripts, then 
``runtest.sh`` may just execute a test script written in another language
(such as Python). Technically, you can even write ``runtest.sh`` itself using
something other than shell script by setting the shebang line appropriately,
but the mandatory ``.sh`` extension makes it inadvisable to actually do so.

For now, let's dissect the shell script version. Firstly, we have ``Server()``
and ``Client()`` functions which will be executed by recipes with the
:envvar:`SERVERS` and :envvar:`CLIENTS` role respectively.

Then we test for :envvar:`JOBID` to determine if the script is running inside
a Beaker instance or if it's being run on the test developer's local
workstation or any other non-Beaker system.

The tests comparing :envvar:`SERVERS` and :envvar:`CLIENTS` to
:envvar:`HOSTNAME` determine what code to run on this particular
machine. As mentioned before, since only one recipe in our
recipe set uses each role, the :envvar:`SERVERS` and :envvar:`CLIENTS`
environmental variables will be set to their respective machines' names
and exported on both machines.

For most meaningful multi-host tests, there will have to be some sort of
coordination and synchronization between the machines and the execution
of the test code on both sides. While in some cases, this may be handled
by a dedicated recipe with the :envvar:`DRIVER` role, Beaker also offers
two utilities for this purpose: :ref:`rhts-sync-set` and
:ref:`rhts-sync-block`.

The :program:`rhts-sync-set` command is used to set a state on a machine.
The :program:`rhts-sync-block` command is used to block the execution of the
task until a certain state on certain machine(s) is reached. Those familiar
with parallel programming can think of this as a barrier operation .
A brief overview of the usage of these utilities:

*  :program:`rhts-sync-set`: This command sets the state of the current
   machine to an arbitrary text string. Syntax: ``rhts-sync-set -s STATE``

*  :program:`rhts-sync-block`: This command blocks execution and doesn't
   return until the specified ``STATE`` is set on the specified machine(s).
   Syntax:
   ``rhts-sync-block -s STATE [-s STATE1 -s STATE2] machine1 machine2 ...``

The role related environment variables can be useful here, as they contain
the hostnames of all recipes in the recipe set with that role. For example,
you can wait for all recipes with the :envvar:`SERVERS` role to set their
state to ``"READY"`` by running::

    rhts-sync-block -s READY $SERVERS

There are a few more important points to consider when writing multihost
tests. Firstly, any multihost testing must ensure that the task execution
order aligns correctly on all machines. For example, the below will fail:

::

              <recipe>
                <task role='STANDALONE' name='/distribution/install'/>
                <task role='STANDALONE' name='/my/test/number1'/>
                <task role='SERVERS'    name='/my/multihost/test'/>
              </recipe>
              <recipe>
                <task role='STANDALONE' name='/distribution/install'/>
                <task role='CLIENTS'    name='/my/multihost/test'/>
              </recipe>

This will fail, because the multihost test is the 3rd test on the server
side and it's the 2nd test on the client side.. To fix this, you can pad
in dummy test cases on the side that has fewer test cases. There is a
dummy test that lives in /distribution/utils/dummy for this purpose. So,
the above can be fixed as:

::

              <recipe>
               <task role='STANDALONE' name='/distribution/install'/>
               <task role='STANDALONE' name='/my/test/number1'/>
               <task role='SERVERS'    name='/my/multihost/test'/>
              </recipe>
              <recipe>
               <task role='STANDALONE' name='/distribution/install'/>
               <task role='STANDALONE' name='/distribution/utils/dummy'/>
               <task role='CLIENTS'    name='/my/multihost/test'/>
              </recipe>

Secondly, by default the :program:`rhts-sync-block` utility will block until
the local or external watchdog is triggered if the expected state is never
achieved. If this behaviour isn't desired, the
:option:`--timeout <rhts-sync-block --timeout>` option can be used
instead. In that case, a zero return code indicates that the desired state
was reached, while a non-zero return code indicates the operation timed out.

Finally, these commands require a bit of manual intervention when run in
the standalone execution environment for Beaker task development, as the
Beaker lab controller normally coordinates the barrier operation. See
:ref:`multihost-standalone`.


Example ``runtest.sh`` for a multihost task
-------------------------------------------

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
        rhts_sync_block -s "DONE" ${SERVERS}

        user="finger1"
        for i in ${SERVERS}
        do
            echo "-- finger user \"$user\" from server \"${i}\"."
            ./finger_client "${i}" "${user}"
            # It returns non-zero for failure.
            if [ $? -ne 0 ]; then
                rhts_sync_set -s "DONE"
                report_result "${TEST}" "FAIL" 0
                exit 1
            fi
        done

        echo "-- client finishes."
        rhts_sync_set -s "DONE"
        result="PASS"
    }

    server()
    {
        # Start server and check it is up and running.
        /sbin/chkconfig finger on && sleep 5
        if ! netstat -a | grep "finger" ; then
            rhts_sync_set -s "DONE"
            report_result "${TEST}" "FAIL" 0
            exit 1
        fi
        useradd finger1
        echo "-- server finishes."
        rhts_sync_set -s "DONE"
        rhts_sync_block -s "DONE" ${CLIENTS}
        result="PASS"
    }

    # ---------- Start Test -------------
    result="FAIL"
    if echo "${CLIENTS}" | grep "${:envvar:`HOSTNAME`}" >/dev/null; then
        echo "-- run finger test as client."
        TEST=${TEST}/client
        client
    fi
    if echo "${SERVERS}" | grep "${:envvar:`HOSTNAME`}" >/dev/null; then
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

Then you just run the script on both client and server. When scripts
reach the :program:`rhts-sync-block` synchronization command they will
display a prompt asking for confirmation of the actual state of the
client/server by keyboard. Generally, this means checking each of the tests
to make sure they've reached the appropriate state (:program:`rhts-sync-set`
will display the state change on stdout), and then confirming this at the
:program:`rhts-sync-block` prompt by hitting Enter.
