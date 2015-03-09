bkr policy-list will retrieve the active access policy
======================================================

Beaker 20 introduces the concept of predefined access policies which
allows a system to either use a custom access policy or a system pool
policy. The ``bkr policy-list`` will by default retrieve the currently
active policy which could be a system pool policy. The ``--custom``
switch can be specified to retrieve the custom access policies
instead even if it is not the currently active access policy.
