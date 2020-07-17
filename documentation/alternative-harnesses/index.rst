.. _alternative-harnesses:

Alternative Harness Guide
=========================

This guide is for Beaker users who want to use a different harness than Beah in 
their recipes.

Selecting an alternative harness in your recipe
-----------------------------------------------

Use the ``harness`` kickstart metadata variable to select an alternative harness.

The default value is ``beah``, which activates the traditional kickstart 
template logic for configuring ``/etc/beah_beaker.conf`` and installing Beah.

When set to any other value, Beah-specific parts of the template are skipped. 
Instead, the kickstart will contain a command to install the named harness. For 
example::

    <recipe ks_meta="harness=my-alternative-harness">
        ...
    </recipe>

will cause the following command to appear in the kickstart ``%post`` section::

    yum -y install my-alternative-harness

The value of the ``harness`` variable will be substituted directly into the 
``yum install`` command line. You can give a package name, assuming your recipe 
also defines a custom yum repo where your harness will be installed from. Or 
you can give an absolute URL to your harness package. If necessary, you can 
pass multiple package names or URLs separate by spaces (remember to quote the 
value correctly).

Environment variables
---------------------

Beaker configures the following system-wide environment variables. When 
installed, a harness implementation must arrange to start itself on reboot and 
then configure itself according to these values.

``BEAKER_LAB_CONTROLLER_URL``
    Base URL of the Beaker lab controller. The harness communicates with Beaker 
    by accessing HTTP resources (described below) underneath this URL.

``BEAKER_LAB_CONTROLLER``
    The fully-qualified domain name of the lab controller to which this system 
    is attached. This will always match the hostname portion of 
    ``BEAKER_LAB_CONTROLLER_URL`` but is provided for convenience.
    
``BEAKER_RECIPE_ID``
    The ID of the Beaker recipe which this system is currently running. Use 
    this to fetch the recipe details from the lab controller as described 
    below.

``BEAKER_HUB_URL``
    Base URL of the Beaker server. Note that the harness should not communicate 
    with the server directly, but it may need to pass this value on to tasks.

.. _harness-http-api:

HTTP resources
--------------

The lab controller exposes the following HTTP resources for use by the harness. 
All URL paths given below are relative to the value of the 
``BEAKER_LAB_CONTROLLER_URL`` environment variable.

When using the :http:method:`POST` method with the resources described below, 
the request body must be given as HTML form data 
(:mimetype:`application/x-www-form-urlencoded`).

.. _lc-api-get-recipe:

.. http:get:: /recipes/(recipe_id)/

   Returns recipe details. Response is in Beaker job results XML format, with 
   :mimetype:`application/xml` content type.
   The root node of the returned XML will be ``<job/>``, which will contain
   the requested recipe element. Note that guest recipes will be nested within
   a partially populated ``<recipe/>``.

.. http:get:: /recipes/(recipe_id)/watchdog

   Returns the number of seconds remaining on the watchdog timer for a recipe.

   The response is a JSON object with a key *seconds*.

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

.. http:patch:: /recipes/(recipe_id)/tasks/(task_id)/

   Updates the attributes of a task. The request must be 
   :mimetype:`application/x-www-form-urlencoded` or 
   :mimetype:`application/json` containing one or more attributes to update.

   :form status:
        Current status of the task. Must be *Running*, *Completed*, or 
        *Aborted* (see the note below about valid transitions).
   :form name:
        Name of the task. This is presented to the user in the recipe results. 
        The harness may determine the name by reading it from metadata 
        associated with the task (for example, RHTS-format tasks define their 
        name in :file:`testinfo.desc`).
   :form version:
        Version of the task which is running. This is recorded in the recipe 
        results to aid in debugging and reproduceability.
   :status 200:
        The task was successfully updated. The response body contains the 
        updated attributes.
   :status 400:
        Bad parameters were given.
   :status 409:
        The requested status transition is invalid.

   Tasks in Beaker always start out having the *New* status. Once a task is 
   *Running*, its status may only change to *Completed*, meaning that the task 
   has completed execution, or *Aborted*, meaning that the task's execution did 
   not complete (or never began) because of some unexpected condition. Once 
   a task is *Completed* or *Aborted* its status may not be changed. Attempting 
   to change the status in a way that violates these rules will result in 
   a :http:statuscode:`409` response.

.. http:post:: /recipes/(recipe_id)/tasks/(task_id)/status

   .. deprecated:: 0.16
      Use :http:patch:`/recipes/(recipe_id)/tasks/(task_id)/` instead.

   Updates the status of a task. See the note above about valid transitions for 
   the status attribute.

   :form status: The new status. Must be *Running*, *Completed*, or *Aborted*.
   :status 204: The task status was updated.
   :status 400: Bad parameters given.
   :status 409: Requested state transition is invalid.

.. http:post:: /recipes/(recipe_id)/tasks/(task_id)/results/

   Records a task result. Returns a :http:statuscode:`201` response with a 
   :mailheader:`Location` header in the form 
   ``/recipes/(recipe_id)/tasks/(task_id)/results/(result_id)``.

   Results may not be recorded against a task after it has finished.

   :form result: The result. Must be *Pass*, *Warn*, *Fail*, *Skip*, or *None*.
   :form path: Path of the result. Conventionally the top-level result will be 
        recorded as ``$TEST``, with sub-results as ``$TEST/suffix``, but this 
        is not required. If not specified, the default is ``/``.
   :form score: Integer score for this result. The meaning of the score is 
        defined on a per-task basis, Beaker intentionally enforces no meaning.
   :form message: Textual message to accompany the result. This is typically 
        short, and is expected to be displayed in one line in Beaker's web UI. 
        Use the log uploading mechanism to record test output.
   :status 201: New result recorded.
   :status 400: Bad parameters given.
   :status 409: Task is already finished.

.. http:put::
   /recipes/(recipe_id)/logs/(path:path)
   /recipes/(recipe_id)/tasks/(task_id)/logs/(path:path)
   /recipes/(recipe_id)/tasks/(task_id)/results/(result_id)/logs/(path:path)

   Stores a log file.

   Log files may not be stored against a recipe or task after it has finished.

   :status 204: The log file was updated.
   :status 409: The recipe or task is already finished.

   Use the :mailheader:`Content-Range` header to upload part of a file.

.. http:get::
   /recipes/(recipe_id)/logs/(path:path)
   /recipes/(recipe_id)/tasks/(task_id)/logs/(path:path)
   /recipes/(recipe_id)/tasks/(task_id)/results/(result_id)/logs/(path:path)

   Returns an uploaded log file.

   Use the :mailheader:`Range` header to request part of a file.

.. http:get::
   /recipes/(recipe_id)/logs/
   /recipes/(recipe_id)/tasks/(task_id)/logs/
   /recipes/(recipe_id)/tasks/(task_id)/results/(result_id)/logs/

   Returns a listing of all uploaded logs.
   
   Possible response formats include an HTML index (:mimetype:`text/html`) or 
   an Atom feed (:mimetype:`application/atom+xml`). Use the 
   :mailheader:`Accept` header to request a particular representation. The 
   default is HTML.

.. http:put:: /power/(fqdn)/

   Commands Beaker to perform given power action on system defined by FQDN.
   The request must be :mimetype:`application/x-www-form-urlencoded` or
   :mimetype:`application/json`.

   :form action:
        Must be *on*, *off*, or *reboot*.
   :status 204:
        The command was successfully executed.
   :status 400:
        Bad parameters were given.

.. http:head:: /healthz/

   Check health status of Harness API.

   :status 200: API is healthy.

.. http:get:: /healthz/

   Check health status of Harness API.

   The response is a message signaling a healthy state.

   :status 200: API is healthy.
