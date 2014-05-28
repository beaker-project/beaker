Force system provisioning
=========================

It is now possible to force Beaker to choose a specified system
irrespective of whether it's Automated, Manual or Broken. Two ways in
which this feature can be used are:

Job XML
~~~~~~~

A new attribute ``force`` has been added to ``<hostRequires/>``
element to allow provisioning a system even though it may be set to
``Manual`` or ``Broken``. This attribute is mutually exclusive with
any other existing host selection criteria such as those specified by
``<system>``. 

For example::

    <hostRequires force='my.host.example.com'/> 

will force the job to run on ``my.host.example.com``.


``bkr machine-test``
~~~~~~~~~~~~~~~~~~~~

``bkr machine-test`` now accepts a ``--ignore-system-status`` switch which allows
testing a system irrespective of the system's status.

Restrictions set via access policy still apply.

(Contributed by Amit Saha in :issue:`851354`.)

