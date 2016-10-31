Log URLs in job results XML
===========================

The job results XML format now includes the filename and URL for each log file 
which was uploaded by the job. Each log is represented by a ``<log/>`` element 
and is contained in a ``<logs/>`` element, which appears inside the 
``<recipe/>``, ``<task/>``, and ``<result/>`` elements.

In case the job results XML with logs is too large, you can request the 
original format without logs by passing the :option:`--no-logs
<bkr job-results --no-logs>` option to the :program:`bkr job-results` command.

(Contributed by Dan Callaghan in :issue:`915319`.)
