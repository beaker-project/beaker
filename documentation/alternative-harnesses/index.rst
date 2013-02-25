Alternative Harness Guide
=========================

This guide is for Beaker users who want to use a different harness than Beah in 
their recipes.

.. admonition:: These interfaces are currently provisional

   There may be minor backwards-incompatible changes made in future versions of 
   Beaker. Once the interfaces have been validated, they will be declared 
   "stable" and no further backwards-incompatible changes will be made to them.

HTTP resources
--------------

The lab controller exposes the following HTTP resources for use by the harness.

When using the :http:method:`POST` method with the resources described below, 
the request body must be given as HTML form data 
(:mimetype:`application/x-www-form-urlencoded`).

.. http:get:: /recipes/(recipe_id)/

   Returns recipe details. Response is in Beaker job results XML format, with 
   :mimetype:`application/xml` content type.

.. http:post:: /recipes/(recipe_id)/watchdog

   Extends the watchdog for a recipe.

   :form seconds: The watchdog kill time is updated to be this many seconds 
        from now.
   :status 204: The watchdog was updated.

.. http:post:: /recipes/(recipe_id)/status

   Updates the status of all tasks which are not already finished.

   :form status: The new status. Must be *Aborted*.
   :status 204: The task status was updated.
   :status 400: Bad parameters given.

   Typically the harness will update the status of each task individually as it 
   runs (see below). This is provided as a convenience only, to abort all tasks 
   in a recipe.

.. http:post:: /recipes/(recipe_id)/tasks/(task_id)/status

   Updates the status of a task.

   :form status: The new status. Must be *Running*, *Completed*, or *Aborted*.
   :status 204: The task status was updated.
   :status 400: Bad parameters given.
   :status 409: Requested state transition is invalid.

   Tasks in Beaker always start out having the *New* status. Once a task is 
   *Running*, its status may only change to *Completed*, meaning that the task 
   has completed execution, or *Aborted*, meaning that the task's execution did 
   not complete (or never began) because of some unexpected condition. Once 
   a task is *Completed* or *Aborted* its status may not be changed. Attempting 
   to change the status in a way that violates these rules will result in 
   a :http:statuscode:`409` response.

.. http:post:: /recipes/(recipe_id)/tasks/(task_id)/results/

   Records a task result. Returns a :http:statuscode:`201` response with a 
   :mailheader:`Location` header in the form 
   ``/recipes/(recipe_id)/tasks/(task_id)/results/(result_id)``.

   :form result: The result. Must be *Pass*, *Warn*, or *Fail*.
   :form path: Path of the result. Conventionally the top-level result will be 
        recorded as ``$TEST``, with sub-results as ``$TEST/suffix``, but this 
        is not required. If not specified, the default is ``/``.
   :form score: Integer score for this result. The meaning of the score is 
        defined on a per-task basis, Beaker intentionally enforces no meaning. 
        If not specified, the default is zero.
   :form message: Textual message to accompany the result. This is typically 
        short, and is expected to be displayed in one line in Beaker's web UI. 
        Use the log uploading mechanism to record test output.
   :status 201: New result recorded.
   :status 400: Bad parameters given.

.. http:put::
   /recipes/(recipe_id)/logs/(path:path)
   /recipes/(recipe_id)/tasks/(task_id)/logs/(path:path)
   /recipes/(recipe_id)/tasks/(task_id)/results/(result_id)/logs/(path:path)

   Stores a log file.

   :status 204: The log file was updated.

   Use the :mailheader:`Content-Range` header to upload part of a file.
