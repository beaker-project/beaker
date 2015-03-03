Changes in the supported queries
================================

Beaker 20 introduces support for systems to either choose between a
custom access policy or using a predefined access policy. The
currently active access policy is referred to by the database column
``active_access_policy_id`` in the ``system`` table and hence the
``custom_access_policy_id`` column should not be used in queries since it may
not be the currently active policy.
