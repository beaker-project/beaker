Turn off readahead service for RHEL6 only
=========================================

Previously, readahead package was excluded during installation for all distros
because it is known to conflict with auditd, but actually it is just neccessary
to turn off the readahead service on RHEL6 only. Now the ``readahead_packages``
snippet is removed and ``readahead_sysconfig`` snippet is enabled for RHEL6
distros only.

Related bugs:

- :issue:`561486`
- :issue:`807991`
