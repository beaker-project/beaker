Provision Atomic images
=======================

This release adds support for for provisioning "rpm-ostree" based Project
Atomic distributions. The feature variable "has_rpmostree" should be used to
identify such a distribution. On such distros, the test harness will be
run in a Docker container rather than on the host system itself.

(Contributed by Amit Saha in :issue:`1148673`)

