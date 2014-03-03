Force system provisioning
=========================

A new attribute ``force`` has been added to ``<hostRequires/>``
element to allow provisioning a system even though it may be set to
``Manual`` or ``Broken``. This attribute is mutually exclusive with
any other existing host selection criteria such as those specified by
``<system>``. 

For example::

    <hostRequires force='my.host.example.com'/> 

will force the job to run on ``my.host.example.com``. 

Restrictions set via access policy still apply.

(Contributed by Amit Saha in :issue:`851354`.)

