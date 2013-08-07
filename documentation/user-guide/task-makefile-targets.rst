Task Makefile targets
=====================

.. todo:: find a better place for this info

The following Makefile targets are defined by the ``rhts-make.include`` which 
is included by every task's Makefile. You can use these targets when updating 
your task.

The Makefile assumes your task is tracked by Git, Subversion, or CVS. Other 
version control systems are not supported. If you are developing a new task 
which is not hosted in any remote version control system, run ``git init`` to 
create a new local git repository to track your work.

``make tag``
    Tags the next release of the task. Run this after committing your changes, 
    so that your updated task has a higher RPM Version-Release for uploading to 
    Beaker.

``make rpm``
    Builds an RPM for this task. You can submit the RPM to Beaker, and it will 
    be downloaded by the harness when a recipe includes this task.

``make bkradd``
    Builds an RPM and submits it to Beaker using :ref:`bkr task-add 
    <bkr-task-add>`.
