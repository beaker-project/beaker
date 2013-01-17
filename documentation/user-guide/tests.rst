Tests
=====

Test architecture considerations
--------------------------------

If you want your test to be smart, that intelligence must be in the
test; the Beaker API can help. A test running in an automated
environment does not have intelligence, hunches, or the ability to
notice unusual activity. This intelligence must be programmed into the
test. Naturally the return on investment for time required to add this
intelligence should be considered, however the more intelligence a test
has to handle false failures and false passes, the more valuable the
automation is to the entity running it. Contrasted with manual testing
where tests are run on a local workstation and suspicious results can be
investigated easily, many organizations find that well written tests
which can be trusted save time that can be used for any number of other
activities.

*Questions to consider*

-  What is needed for a test run to return PASS?

-  What is needed for a test run to return FAIL?

-  How will PASS and FAIL conditions be determined pragmatically?

-  If it is not possible for a test to ever FAIL, does it make sense to
   automate it?

*Things to Keep in Mind*

-  Assume that nothing works:

   -  The test could be running in an unstable test environment.

   -  The package under test might be broken.

   -  An apparently-unrelated component might cause your test to fail in
      an unexpected way.

   -  The system might not be configured in the manner in which you
      expect.

   -  The test may be buggy, reporting false positives or false
      negatives.

-  Identifying potential problem sections in a test can save someone,
   possibly you, hours of debugging time.

*Writing Good Test Code*

-  Check everything: all exit statuses, return values from function
   calls, etc. Unfortunately there are plenty of programs which return
   success codes even when a failure occurs.

-  Capture all debug output that might indicate an error; it may give
   clues as to what is going wrong when a test fails.

-  Comment your tests; good comments should describe the intent of what
   you are doing, along with caveats being followed, rather than simply
   parroting the code back as pseudo code.

-  In most (ideally all) situations a test should report true PASS and
   FAIL results, but test code is still code, and will invariably
   contain bugs.

-  Program defensively so that errors in test code report false FAIL
   results rather than false PASSes. For example, initialize a result
   variable to FAIL and only set it to PASS if no errors are detected.

-  Do not initialize a variable to PASS which fails only on a specific
   error -- what if you missed another error? What if the shell
   function you called failed to execute?

-  It is easier to investigate and fix a failed test than a test that
   always passes (which it should not be).

Writing and running multihost tasks
-----------------------------------

All of the examples so far have run on a single host. Beaker has support
for tasks that run on multiple hosts, e.g. for testing the interactions
of a client and a server.

When a multihost task is run in the lab, a machine will be allocated to
each role in the test. Each machine has its own recipe.

Each machine under test will need to synchronize to ensure that they
start the test together, and may need to synchronize at various stages
within the test. Beaker has three notional roles: client, server and
driver.

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

-  *CLIENTS* contains a space-separated list of hostnames of clients
   within this recipeset.

-  *SERVERS* contains a space-separated list of hostnames of servers
   within this recipeset.

-  *DRIVER* is the hostname of the driver of this recipeset, if any.

The variable HOSTNAME can be used by runtest.sh to determine its
identity. It is set by rhts-environment.sh, and will be unique for each
host within a recipeset.

Your test can thus decide whether it is a client, server or driver by
investigating these variables: see the example below.

When you are developing your test outside the lab environment, only
HOSTNAME is set for you (when sourcing the rhts-environment.sh script).
Typically you will copy your test to multiple development machines, set
up CLIENTS, SERVERS and DRIVER manually within a shell on each machine,
and then manually run the runtest.sh on each one, debugging as
necessary.

A multihost test needs to be marked as such in the\ *Type: Multihost*.

In it's simplest form, a job with multihost testing can look like::

    <job>
      <RecipeSet>
         <recipe>
            <task role='STANDALONE' name='/distribution/install'/>
            <task role='SERVERS' name='/my/multihost/test'/>
         </recipe>
         <recipe>
            <task role='STANDALONE' name='/distribution/install'/>
            <task role='CLIENTS' name='/my/multihost/test'/>
         </recipe>
      </RecipeSet>
    </job>

.. note:: For brevity some necessary parts are left out in the above job
   description

Submitting the job above will export environmental variables SERVERS and
CLIENTS set to their respective hostnames. This allows a tester to write
tests for each machines. So the runtest.sh in /my/multihost/test test
might look like::

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

    if $(echo $SERVERS | grep -q $HOSTNAME); then
        TEST="$TEST/Server"
        Server
    fi

    if $(echo $CLIENTS | grep -q $HOSTNAME); then
        TEST="$TEST/Client"
        Client
    fi

Let's dissect the code. First of, we have Server() and Client() functions
which will be executed on SERVERS and CLIENTS machines respectively.
Then we have an if block to determine if this is running as an beaker
test, or if it's being run on the test developer's machine(s) to test it
out. The last couple if blocks determine what code to run on this
particular machine. As mentioned before, SERVERS and CLIENTS
environmental variables will be set to their respective machines' names
and exported on both machines.

Obviously, there will have to be some sort of coordination and
synchronization between the machines and the execution of the test code
on both sides. Beaker offers two utilities for this purpose,
rhts-sync-set and rhts-sync-block . rhts-sync-set is used to setting a
state on a machine. rhts-sync-block is used to block the execution of
the code until a certain state on certain machine(s) are reached. Those
familiar with parallel programming can think of this as a barrier
operation . The detailed usage information about both of this utilities
is below:

-  *rhts-sync-set*: It does set the state of the current machine. State
   can be anything. Syntax: rhts-sync-set -s STATE

-  *rhts-sync-block*: It blocks the code and doesn't return until a
   desired STATE is set on desired machine(s) . You can actually look
   for a certain state on multiple machines.. Syntax: rhts-sync-block -s
   STATE [-s STATE1 -s STATE2] machine1 machine2 ...

There are a couple of important points to pay attention. First of, the
multihost testing must be on the same chronological order on all
machines. For example, the below will fail:

::

              <recipe>
                <task role='STANDALONE' name='/distribution/install'/>
                <task role='STANDALONE' name='/my/test/number1'/>
                <task role='SERVERS'     name='/my/multihost/test'/>
              </recipe>
              <recipe>
                <task role='STANDALONE' name='/distribution/install'/>
                <task role='CLIENTS'     name='/my/multihost/test'/>
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
               <task role='SERVERS'     name='/my/multihost/test'/>
              </recipe>
              <recipe>
               <task role='STANDALONE' name='/distribution/install'/>
               <task role='STANDALONE' name='/distribution/utils/dummy'/>
               <task role='CLIENTS'     name='/my/multihost/test'/>
              </recipe>

One shortcoming of the rhts-sync-block utility is that it blocks
forever, so if there are multiple things being done in your test between
the hosts, your test will timeout without possibly a lot of code being
executed. There is a utility, blockwrapper.exp which can be used to put
a limit on how many second it should block. The script lives in
/CoreOS/common test, so be sure to add that test before your multihost
tests in your recipes. The usage is exactly same as that of
rhts-sync-block with the addition of a timeout value at the end, i.e.:

::

                        blockwrapper.exp -s STATE machine N 

where N is the timeout value in seconds. If the desired state in the
desired machine(s) haven't been set in N seconds, then the script will
exit with a non-zero return code. In case of success it'll exit with
code 0 .

Synchronization commands
~~~~~~~~~~~~~~~~~~~~~~~~

Synchronization of machines within a multihost test is performed using
per-host state strings managed on the Beaker server. Each machine's
starting state is the empty string.

::

    rhts-sync-set -s state 

The rhts-sync-set command sets the state of this machine within the test
to the given value.

::

    rhts-sync-block -s state [hostnames...] 

The rhts-sync-block command blocks further execution of this instance of
the script until all of the listed hosts are in the given state.

Unfortunately, there is currently no good way to run these commands in
the standalone helper environment.

Example of a runtest.sh for a multihost test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    if echo "${CLIENTS}" | grep "${HOSTNAME}" >/dev/null; then
        echo "-- run finger test as client."
        TEST=${TEST}/client
        client
    fi
    if echo "${SERVERS}" | grep "${HOSTNAME}" >/dev/null; then
        echo "-- run finger test as server."
        TEST=${TEST}/server
        server
    fi
    echo "--- end of runtest.sh."
    report_result "${TEST}" "${result}" 0
    exit 0

Tuning up multihost tests
^^^^^^^^^^^^^^^^^^^^^^^^^

Multihost tests can be easily tuned up outside Beaker using following
code snippet based on $JOBID variable (which is set when running in
Beaker environment). Just log in to two machines (let's say:
client.example.com and server.example.com) and add following lines at
the beginning of your runtest.sh script.

::

    # decide if we're running on RHTS or in developer mode
    if test -z $JOBID ; then
            echo "Variable JOBID not set, assuming developer mode"
            CLIENTS="client.example.com"
            SERVERS="server.example.com"
    else
            echo "Variable JOBID set, we're running on RHTS"
    fi
    echo "Clients: $CLIENTS"
    echo "Servers: $SERVERS"

Then you just run the script on both client and server. When scripts
reach one of the synchronization commands (rhts-sync-set or
rhts-sync-block) you will be asked for supplying actual state of the
client/server by keyboard (usually just confirm readiness by hitting
Enter). That's it! :-)

Reporting results
-----------------

The philosophy of Beaker is that the engineers operating the system will
want to quickly survey large numbers of tests, and thus the report
should be as simple and clear as possible. "PASS" indicates that
everything completed as expected. "FAIL" indicates that something
unexpected occurred.

In general, a test will perform some setup (perhaps compiling code or
configuring services), attempt to perform some actions, and then report
on how well those actions were carried out. Some of these actions are
your responsibility to capture or generate in your script:

-  a PASS or FAIL and optionally a value indicating a test-specific
   metric, such as a performance figure.

-  a debug log of information -- invaluable when troubleshooting an
   unexpected test result. A test can have a single log file and report
   it into the root node of your results tree, or gather multiple logs,
   reporting each within the appropriate child node.

Other components of the result can be provided automatically by the
framework when in a test lab environment:

-  the content of the kernel ring buffer (from dmesg). Each report
   clears the ring buffer, so that if your test reports multiple
   results, each will contain any messages logged by the kernel since
   the last report was made.

-  a list of all packages installed on the machine under test (at the
   time immediately before testing began), including name,
   version/release, and architecture.

-  a separate report of the packages listed in the RunFor of the
   metadata including name, version/release, and architecture (since
   these versions are most pertinent to the test run).

-  if a kernel panic occurs on the machine under test, this is detected
   for you from the console log output, and will cause a Panic result in
   place of a PASS or FAIL for that test.

In addition, the Beaker framework provides a hierarchical namespace of
results, and each test is responsible for a subtree of this namespace.
Many simple tests will only return one result (the node they own), but a
complex test can return an entire subtree of results as desired. The
location in the namespace is determined by the value of variables
defined in the Makefile. These variables will be discussed in the
Packaging section.

A test may be testing a number of related things with a common setup
(e.g. a setup phase of a server package onto localhost, followed by a
collection of tests as a client). Some of these things may not work
across every version/architecture combination. This will produce a list
of "subresults", each of which could be classified as one of:

-  expected success: will lead to a PASS if nothing else fails

-  expected failure: should be as a PASS (as you were expecting it).

-  unexpected success: can be treated as a PASS (since it's a success),
   or a FAIL (since you were not expecting it).

-  unexpected failure: should always be a FAIL

Given that there may be more than one result, the question arises as to
how to determine if the whole test passes or fails. One way to verify
regression tests is to write a script that compares a set of outputs to
an expected "gold" set of outputs which grants PASS or FAIL based on the
comparison.

It is possible to write a script that silently handles unexpected
successes, but it is equally valid for a script to report a FAIL on an
unexpected success, since this warrants further investigation (and
possible updating of the script).

To complicate matters further, expected success/failure may vary between
versions of the package under test, and architecture of the test
machine.

If the test is checking multiple bugs, some of which are known to work,
and some of which are due to be fixed in various successive (Fedora)
updates, ensure that the test checks everything that ought to work,
reporting PASS and FAIL accordingly. If the whole test is reporting a
single result, it will typically report this by ensuring that all
expected things work; as bugs are fixed, more and more of the test is
expected to work and can cause an overall FAIL.

If it is reporting the test using a hierarchy of results, the test can
have similar logic for the root node, and can avoid reporting a result
for a subtree node for a known failure until the bug is fixed in the
underlying packages, and avoid affecting the overall result until the
bug(s) is fixed.

As a general Beaker rule of thumb, a FAIL anywhere within the result
subtree of the test will lead to the result for the overall test being a
FAIL.

Logging tips
~~~~~~~~~~~~

Indicate failure-causing conditions in the log clearly, with "FAIL" in
upper case to make it easier to grep for.

Good log messages should contain three things: # what it is that you are
attempting to do (e.g. checking to see what ls reports for the
permission bits that are set on file foo) # what it is that you expect
to happen (e.g. an expectation of seeing "-rw-r--r--" ) # what the
actual result was an example of a test log showing success might look
like:

::

                Checking ls output: "foo" ought to have permissions "-rw-r--r--"
                    Success:  "foo" has permissions: "-rw-r--r--"

An example of a failure might look like:

::

             Checking ls output: "foo" ought to have permissions "-rw-r--r--"
                 FAIL:  ls exit status 2   

For multihost tests, time stamp all your logs, so you can interleave
them.

Use of tee is also helpful to ensure that the output at the terminal as
you debug a test is comparable to that logged from OUTPUTFILE in the lab
environment.

Past experiences has shown problems where people confuse overwriting
versus appending when writing out each line of a log file. Use tee -a
$OUTPUT rather than tee > $OUTPUT or tee >> $OUTPUT.

Include a final message in the log, stating that this is the last line,
and (for a single-result test) whether the result is a success or
failure; for example:

::

                 echo "----- Test complete: result=$RESULT -----" | tee -a $OUTPUTFILE

Finish your runtest.sh: (after the report\_result) to indicate that the
final line was reached; for example:

::

                 echo "***** End of runtest.sh *****"

Passing parameters to tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you need a test to perform different steps in some specific
situations there is an option available through Simple Workflow command
line interface called --test-params which allows you to pass the
supplied parameter to runtest.sh where you can access it by
TEST\_PARAM\_NAME=value.

For example you can launch the single workflow with a command line like
this:

::

    bkr workflow-simple --arch=i386 --family=RedHatEnterpriseLinuxServer5 --task=/distribution/install --taskparam="SUBMITTED_FROM=CLIENT"

And then make use of the passed parameter inside the runtest.sh script:

::

            if [[ TEST_PARAM_PAR1 == 1 ]] ; then do something; fi

Test writing tips
-----------------

*Reboot count*.
Sometimes it can be useful to ascertain how many times the system has
rebooted. To do this, you can use the environment variable
``REBOOTCOUNT``. Each time the reserved machine is rebooted,
``REBOOTCOUNT`` will be incremented by one.

Using the startup\_test function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The startup\_test function can be used to provide a primitive smoke-test
of a program, by setting a shell variable named result. You will need to
use report\_result if you use it. The syntax is:

::

                startup_test program [arg1] [arg2] [arg3]

The function takes the name of a program, along with up to three
arguments. It fakes an X server for the test by ensuring that Xvfb is
running (and setting DISPLAY accordingly), then enables core-dumping,
and runs the program with the arguments provided, piping standard output
and error into OUTPUTFILE (overwriting, not appending).

The function then checks various things:

-  any Gtk-CRITICAL warnings found in the resulting OUTPUTFILE cause
   result to be WARN.

-  that the program can be found in the PATH, using the which command;
   if it is not found it causes result to be FAIL, appending the problem
   to OUTPUTFILE

-  for binaries, it uses ldd to detect missing libraries; if any are
   missing it causes result to be FAIL, appending the problems to
   OUTPUTFILE

-  if any core dumps are detected it causes result to be FAIL

Finally, it kills the fake X server. You then need to report the result.

::

                #!/bin/sh

                # source the test script helpers
                . /usr/bin/rhts-environment.sh

                # ---- do the actual testing ----
                result=PASS 1 
                startup_test /usr/bin/evolution
                report_result $TEST $result 2 

Normally it's a bad idea to start with a PASS and try to detect a FAIL,
since an unexpected error that prevents further setting of the value
will lead to a false PASS rather than a false FAIL. Unfortunately in
this case the startup\_test function requires it.

::

            report_result $TEST $result 

We report the result, using the special result shell variable set by
startup\_test

Checklist discussed
-------------------

Quality of code
~~~~~~~~~~~~~~~

Check for the following:

-  *Commenting*: Test code is commented and complex routines
   sufficiently documented.

-  *PURPOSE file*: Test code directory contains a plain text file called
   PURPOSE which explains what the test addresses along with any other
   information useful for troubleshooting or understanding it better.

-  *Language-Review*: Optional, but preferred: review by someone with
   language-of-implementation knowledge.

-  *Functional-Review*: Optional, but preferred: functionality
   peer-reviewed (i.e. by someone else) with knowledge of the given
   domain.

Quality of logs
~~~~~~~~~~~~~~~

Check the following attributes to ensure the quality of logs:

-  *Detail of logging*

   -  Test logs should be verbose logging activity for both successful
      and unsuccessful operations. At a minimum these conditions should
      be recorded:

      -  Name of Test (or subtest; something unique)

      -  Expected Result

      -  Actual Result

      -  Whether items 2 and 3 constitute a PASS or a FAIL.

   -  This should help with questions such as:

      -  How many tests ran?

      -  What went wrong on FAILed cases?

      -  How many PASSes/FAILs were there?

-  And, associating the Name+Result with prior runs:

   -  How well are we doing?

Correctness
~~~~~~~~~~~

Correctness has following parameters:

-  *True PASS and true FAIL results*

   -  The test runs and generates true PASS and true FAIL results as
      appropriate. It is permissible for a test to FAIL even if the
      expected result is PASS if the software under test has a known
      defect that has been reported. The applicable bug number should be
      referenced in the error message so that it is easy to research the
      failure.

-  *Watch for bogus success values*

   -  The test verifies PASS and FAIL results (versus returning the
      success or failure from a particular shell command... many shell
      commands return success because they successfully ran, not that
      they returned expected data. This usually requires user
      verification)

-  *Security review*

   -  A cursory review of the code should be performed to make sure it
      does not contain obviously malicious or suspicious routines which
      appear more focused on damaging or casing the testing
      infrastructure versus performing a valid test.

Packaging
~~~~~~~~~

Check the following attributes to ensure the correctness of Packaging:

-  *Makefile*

   -  ``make package`` works correctly, generating an RPM with the
      expected payload. The RPM should successfully install correctly
      without any errors or dependency problems.

   -  ``make clean`` should clean up all generated files that will not
      be stored in source control

   -  All unneeded comments and unused variable should be removed from
      the ``Makefile``.The Makefile template contains lots of ``FIXME``
      comments indicating what to put where. These comments should be
      removed from the final Makefile

   -  Metadata section of ``Makefile`` should have these fields filled
      properly:

      -  Releases (only few tests can correctly run on everything from
         RHEL-2.1 to F8)

      -  RunFor (some tests stresses a lot of RHEL components, so they
         could be all here)

      -  Bug (lot of tests tests specific bug number, it is not enough
         to have it in test name)

   -  ``Permissions``: File permissions should be set appropriately on
      built packages and verified by running\ ``rpm -qplv`` [package
      name]. For example:

      ::

          File permissions should be set appropriately on built packages and verified by running rpm -qplv [package name]. For example: 

      -  ``runtest.sh`` should be executable by all users

      -  any other executables should be executable by all users

      -  ``PURPOSE`` and generated ``testinfo.desc`` should be 644

   -  *Correct namespace* For Correct namespace, double check the
      following:

      -  Confirm that the test is included in the correct namespace and
         has followed the proper naming conventions. Refer to the
         [TOPLEVEL\_NAMESPACE] to make sure that the underlying package
         being tested is reporting results in the correct namespace.

      -  The Makefile variables and test names should also correspond to
         the correct path in source control. For example:

         ::

             [grover@dhcp83-5 smoke-high-load]# pwd
             /home/grover/rhts/tests/bind/smoke-high-load

Here are the applicable variables from the Makefile:

::

    # The toplevel namespace within which the test lives.
    TOPLEVEL_NAMESPACE=CoreOS

    # The name of the package under test:
    PACKAGE_NAME=bind

    # The path of the test below the package:
    RELATIVE_PATH=smoke-high-load
