Install options parsing
=======================

A regression was found in Beaker 0.10 due to which kernel options of the
form ``key1=value1 key1=value2`` were incorrectly added to a recipe as
``key1=value2``. This has now been fixed.

Related bug: :issue:`886875`
