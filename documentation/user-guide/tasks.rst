Tasks
-----

.. _task-searching:

Task searching
~~~~~~~~~~~~~~

To search for a task, select :menuselection:`Scheduler --> Task Library` from
the menu. The default search is on the "Name" property, with the "contains"
operator. Other metadata search attributes are as follows:

-  *Description*
   -  This is the description provided when creating the task.
-  *Version*
   -  This is the version of the task.
-  *Excluded OSMajor*
   -  This searches the Excluded OSMajor list of the task.
-  *Excluded Architecture*
   -  This searches the Excluded Architecures list of the task.
-  *Test Type*
   -  This is the type of test when task was defined.

Refer to :ref:`task_metadata` for further details on metadata
attributes.

Once you've found a particular task, you can see its details by clicking
on the link in the :guilabel:`Name` column.

On the task page you can use the :guilabel:`Executed Tasks` search to search
history of past executions of the task.

.. _adding-tasks:

Uploading a task
~~~~~~~~~~~~~~~~

If you already have a task packaged as an RPM, select :menuselection:`Scheduler
--> New Task` from the menu. Click the :guilabel:`Browse` button to
locate the task RPM on your local system, and then click the :guilabel:`Submit
Data` button to upload it. See :ref:`bkr task-add <bkr-task-add>` for how to do
this via the beaker client.

If you are updating an existing task, the version of the new task RPM must be
higher than the existing version. This can be achieved by running ``make tag``
(if the task is stored in version control), or manually adjusting the
``TESTVERSION`` variable in the task's ``Makefile`` (see
:ref:`makefile-variables`).

If you are uploading a new task, the rpm must contain a testinfo.desc file
which contains all the mandatory fields described in the metadata section
(see :ref:`testinfo.desc`).
