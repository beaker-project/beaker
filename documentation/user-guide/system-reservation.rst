.. _system-reserve:

Reserving a system after testing
================================

After the tests have completed, it may be desirable to reserve the
test system to collect any additional logs, perform any additional
testing or verify the test results manually. Reserving a system
prevents Beaker from claiming back the system automatically and can be
accomplished using one of the following methods.

Using the ``/distribution/reservesys`` task
-------------------------------------------

When the :ref:`/distribution/reservesys task <reservesys-task>`
is added to a recipe, it will reserve the system until the system is
explicitly returned or the reservation duration expires. If the
reservation is explicitly returned, then execution resumes with the
next task, or, if there are no remaining tasks, the recipe is marked
as ``Completed``. If the reservation duration instead expires, then
the recipe is aborted entirely and no further tasks are executed.

An example recipe skeleton is as follows::

    <recipe>
      ..
      <task name='/distribution/mytask1'/>
      <task name='/distribution/mytask2'/>
      <task name='/distribution/reservesys'/>
      ..
    </recipe>

The above will reserve the system after the two tasks, 
``/distribution/task1`` and ``/distribution/task2`` have finished
execution. The recipe status will be "Running" during the duration of
the system being reserved.

Configuring the reservation behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The reservation behavior can be configured with the help of the
following task parameters:

- :envvar:`RESERVE_IF_FAIL`: If this parameter is defined then the
  result of the recipe is checked. The system is reserved, *only* if the
  recipe did not pass. If it passed, this "test" is reported back to
  Beaker as a pass and the next task in the recipe (if any) begins
  execution. The parameter should be defined as: ``<param
  name="RESERVE_IF_FAIL" value= "True" />`` (While *any* non-empty string
  will have the same effect, using the string ``"True"`` is strongly
  recommended). If you want to reserve the system irrespective of the
  result of the test, do not specify this variable at all.

- :envvar:`RESERVETIME`: Using this parameter, you can define the duration
  (in seconds) for which you want to reserve the system up to a maximum
  of 356400 seconds (99 hours). If this variable is not defined, the
  default reservation is for 86400 seconds (24 hours). You can return
  the system early as described in :ref:`return-early-extend-time`.

For example, to define both these parameters when you specify the task
in your job description, you would use the following::

    <task name="/distribution/reservesys" role="STANDALONE">
      <params>
        <param name="RESERVE_IF_FAIL" value="True" />
        <param name="RESERVETIME" value="172800" />
      </params>
    </task>

.. note::

   Due to an `unfortunate race condition
   <https://bugzilla.redhat.com/show_bug.cgi?id=989294>`__,
   conditional reservation may be unreliable if the immediately preceding
   task is the only one that fails in the recipe. Inserting
   :ref:`dummy-task` prior to this task may help if
   the problem of failing to reserve the system occurs regularly.

Notification
~~~~~~~~~~~~

Depending on whether you set the :envvar:`RESERVE_IF_FAIL` parameter
appropriately and its implications (as described), once the system has
been reserved, you will receive an email with the subject "[Beaker
Machine Reserved] test-system.example.com" and other information. This
is a notification that the system has now been reserved and you can
connect to it (using an SSH client, either using the username and
password or your public key).

The notification email is sent from the test system. This implies that
in case of a problem in network connectivity between your email server
and the test system, the notification email will not be received.

.. _return-early-extend-time:

Returning early and extending reservation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The email also includes information about returning the system
early or extending your reservation time. To return the system early,
execute :program:`return2beaker.sh` from your terminal (after you have
logged in to the system).

To extend the reservation time, execute :program:`extendtesttime.sh`
and enter the desired extension to the reservation (relative to the current
time).

Changes to the test system environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Besides creating the above scripts on the test system in
:file:`/usr/bin`, the task also sets up a custom message in
:file:`/etc/motd`. When you login to the reserved system, you 
will be greeted with a custom message and you will find
the two scripts accessible from your shell. These changes
are in addition to the RPM packages installed to meet the
dependencies for the task.

.. _reservesys:

Using the ``<reservesys/>`` element
-----------------------------------

.. versionadded:: 0.17.0

If this element is added to a recipe, it will reserve the system after
all the tasks have finished execution (or when the recipe is aborted
as described below). By default, it reserves the system for 86400
seconds (or 24 hours), but this can be changed  using the ``duration``
attribute. For example, ``<reservesys duration="3600"/>`` will reserve
the system for an hour.

An example recipe skeleton using this approach is as follows::

    <recipe>
      ..
      <task name='/distribution/mytask1'/>
      <task name='/distribution/mytask2'/>
      <reservesys/>
      ..
    </recipe>

After both the tasks have finished execution, the system will be
reserved. The recipe status will be "Reserved" during the duration of
the system being reserved.

You can also conditionally reserve the system at the end of your recipe by using
the attribute ``when=""``, with the following values:

``onabort``
  The system will be reserved if the recipe status is Aborted.
``onfail``
  The system will be reserved if the recipe status is Aborted, or the result is 
  Fail.
``onwarn``
  The system will be reserved if the recipe status is Aborted, or the result is 
  Fail or Warn. This corresponds to the existing ``RESERVE_IF_FAIL=1`` option 
  for the ``/distribution/reservesys`` task.
``always``
  The system will be reserved unconditionally.

If this element is given without a ``when=""`` attribute, it defaults to
``when="always"``, matching the behaviour from previous Beaker versions.

The advantage of using this approach is that this will also reserve
the system under abnormal circumstances which cause the recipe to be
aborted. Circumstances in which this may happen include a
hung task, installation failures, kernel panics, the test harness
rendered non-functional for some reason and others. Thus, this is a
more robust way of reserving a system.

Notification email
~~~~~~~~~~~~~~~~~~

Once the system is reserved, an email notification will be sent to the
job owner with the subject "[Beaker System Reservation] System:
test-system.example.com" The email content is slightly different from the
previous case, but includes similar information such as the hostname of the
system reserved, the distribution provisioned on the system, how to
return the reservation and others. The notification email is sent from the
Beaker server, and hence any abnormal condition on the test system
doesn't affect this.

Returning early and extending reservation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once a system is reserved, the remaining duration is shown at the top of the
recipe page with the label :guilabel:`Remaining watchdog time`. To
return the system, click the :guilabel:`Return the reservation` button on the
:guilabel:`Reservation` tab.

On the :guilabel:`Reservation` tab, you can extend the reservation by clicking
on the :guilabel:`Extend the reservation` button and enter how much time the
reservation should be extended by. You can also extend it by using the
:program:`bkr watchdog-extend` command.

Changes to the test system environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As a consequence of the fact that system reservation using this method
is completely external to the test system, the test
system will be in a state exactly what it was at the end of executing the
last task when it's reserved. A standard Beaker test system message is
displayed when you login.
