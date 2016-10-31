Timestamps in job results XML
=============================

The job results XML format now includes the following additional timestamp 
attributes:

* ``start_time`` and ``finish_time`` on the ``<recipe/>`` element
* ``start_time`` and ``finish_time`` on the ``<task/>`` element
* ``start_time`` on the ``<result/>`` element

Timestamps are in the form ``YYYY-mm-dd HH:MM:SS`` and expressed in UTC.

(Contributed by Dan Callaghan in :issue:`1037594`.)
