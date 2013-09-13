ntp is not removed by default
-----------------------------

Previously the ``ntp`` package was excluded in favour of ``chrony``
when installing Fedora or Red Hat Enterprise Linux 7. To avoid
interfering with tasks which require ``ntp``, the package is no longer
excluded. However if ``chrony`` and ``ntp`` are both installed, the
``ntpd`` service is disabled to prevent conflicts with ``chronyd``.

(Contributed by Amit Saha in :issue:`1002928`)
