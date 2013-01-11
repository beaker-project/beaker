Workflow
========

.. toctree::
   virtualization-workflow
   provisioning

Submitting and reviewing a job
------------------------------

To submit a Job you must create a Job description. This is an XML file
containing the tasks you want to run, as well as special environment
variables and other options you want to setup for your Job.

.. admonition:: Valid Job Specs

   If this is the first time running this Job make sure that at least one 
   system with the specified architecture has access to the specified distro 
   and all the relevant tasks are available to Beaker. To do this, See 
   :ref:`system-searching`, :ref:`distro-searching` and :ref:`task-searching` 
   respectively.

To submit the Job, either use the `beaker
client <../installation-guide.html#beaker-client>`__ or :ref:`submit the job
via the UI <submitting-a-new-job>`.

Once Submitted you can view the progress of the Job by going to the :ref:`job
search page <job-searching>`. Once your Job is Completed, see the :ref:`job
results page <job-results>`.

Job XML
-------

You can specify Beaker jobs using an XML file. This allows users a more
consistent, maintainable way of storing and submitting jobs. You can
specify and save entire jobs, including many recipes and recipesets in
them in XML files and save them as regression test suites and such.

The various elements along with their attributes and the values they can
take are described in the RELAX NG schema described in the file
`beaker-job.rng <http://beaker-project.org/schema/beaker-job.rng>`_. See
also :ref:`job-workflow-details`.
