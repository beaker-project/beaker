New result type Skip
====================

Beaker now supports a new result type, Skip. A task can report this result to 
Beaker in the same way that it reports Pass, Fail, or Warn using the standard 
:program:`rhts-report-result` command or its wrappers. You can use this result 
type to indicate that a task is not applicable on a particular platform, for 
example.

(Contributed by Dan Callaghan in :issue:`1324607`.)
