Limits on number of results and result logs per recipe
======================================================

Beaker now enforces an upper limit on the total number of results and result 
logs in a single recipe. By default the limits are 7500 results and 7500 result 
logs, but the Beaker administrator can adjust or disable the limits.

The limits are intended as an extreme upper bound which should not interfere 
with normal testing, but will prevent a runaway task from accidentally 
producing so many results that it can cause problems elsewhere in Beaker (for 
example, very large recipes cause excessive memory usage in 
:program:`beaker-transfer`, :program:`beaker-log-delete`, and when rendering 
results in the web UI).

(Contributed by Dan Callaghan in :issue:`1293007`.)
