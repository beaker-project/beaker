Control the result display format for bkr job-list
===================================================

``bkr job-list`` now accepts a ``--format`` switch and doesn't return
the number of jobs found.

This switch takes two values: ``list`` and ``json``. When the format
is specified as a ``list``, the result is presented to the user such
that each of the Job IDs are on a separate line. This makes it
possible to use the output as an input to other command line
utilities. Hence, for example: ``bkr job-list --mine --format list |
wc -l``, would return the number of jobs found for the user invoking
the command. 

The ``json`` format returns the Job IDs as a JSON
string. This format is compact and is useful for quick human
observation.

If a format is not specified, it returns the result as a JSON string.

Related bugs:
 
- :issue:`907658`
