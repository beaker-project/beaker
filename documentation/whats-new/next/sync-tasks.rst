Script to sync the task RPMs between Beaker instances
=====================================================

``beaker-sync-tasks`` is a server side tool to sync the task RPMs
between two Beaker instances.

Currently, the tool operates in overwrite mode, i.e. it
overwrites tasks of the same name on the destination Beaker instance
with that from the source Beaker instance.

See the section on :ref:`copying tasks <sync-tasks>` in the
:ref:`installation guide <install-guide>` to learn more about how to
use this tool.

Related bugs:
 
- :issue:`912205`
