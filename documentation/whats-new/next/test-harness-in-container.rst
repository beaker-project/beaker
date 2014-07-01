Run test harness in a container
===============================

This release adds initial support for running tests in a Docker
container instead of the host system. The host distribution and
architecture must support running Docker containers for this to work
successfully. The tests are run in a privileged container and hence
the standard security caveats apply.

Specifying the ``contained_harness`` ksmeta variable will run the test harness
in a Docker container and hence the tasks will be executed in
the container instead of the host system.

Example::

    <recipe ks_meta="contained_harness" >
    ..
    ..
    </recipe>

See the description of the ``contained_harness``, ``contained_harness_entrypoint``,
``harness_docker_base_image`` variables in :ref:`kickstart-metadata`
for usage instructions. Tests which need the host system to be
rebooted are not currently supported and neither are tests which may
want to spawn other containers.

(Contributed by Amit Saha in :issue:`1131388`)
