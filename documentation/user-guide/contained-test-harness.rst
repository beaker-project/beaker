.. _tests-in-container:

Running tests in a Container
----------------------------

.. versionadded:: 0.18.3


Beaker supports running the tests in a Docker container instead of the host system.
After the host system is provisioned, the test harness container is created which
then executes the specified tasks in the recipe. `Restraint
<https://restraint.readthedocs.org>`__ is the default test harness
used in the container.

.. note::

  This is an experimental feature and limitations most likely exist other than the 
  ones mentioned later in this guide.

An example Beaker job using this feature is as follows:

.. literalinclude:: contained-test-harness-default.xml

The key points in the above recipe worth noting are:

- The ``no_default_harness_repo`` ksmeta variable tells Beaker to not include
  the repository for Beaker's test harness.
- ``contained_harness`` ksmeta variable: This tells beaker that we want to run 
  the test harness in a Docker container.
- The host distro as specified by ``<distroRequires/>`` is Fedora 20.
- The harness repo needs to be specified as an additional repo using the ``<repo/>`` 
  element. This is different from a "traditional" Beaker recipe since Beaker can 
  figure out the harness repo to be used from the distro being used for the job.
- Since this recipe does not specify which distro image to use for the test harness 
  container, Beaker tries to retrieve the docker image corresponding to the host distro 
  i.e. Fedora 20 in this case.

Specifying the harness docker image
===================================

To specify a different image, use the ``harness_docker_base_image`` ksmeta 
variable. For example, the following recipe will run the test harness in a 
CentOS 7 container while the host system is running Fedora 20:

.. literalinclude:: contained-test-harness-baseimage.xml

The image specified by ``harness_docker_base_image`` is expected to be in a form
usable in a Dockerfile's `FROM <http://docs.docker.com/reference/builder/#from>`__
instruction. One thing to keep in mind is that the distro should use systemd as the 
process manager.

Test harness container entrypoint
=================================

Beaker relies on systemd to initialize the test harness in the container and 
hence the harness container will execute :program:`/usr/sbin/init` (using 
Dockerfile's ``CMD`` instruction) on startup. Hence it is  the harness's 
responsibility to "enable" itself during the installation. This can however 
be changed with the ``contained_harness_entrypoint`` ksmeta variable. 
For example, if your test harness is a standalone binary, you may not want to
use systemd for it. Specifying ``contained_harness_entrypoint=/usr/bin/myharnessd``
will ensure that the harness runs :program:`/usr/bin/myharnessd` instead of 
:program:`/usr/sbin/init`.


Limitations
===========

This is an experimental feature and currently the following known limitations exist:

- The host OS must use systemd process manager and capable of running Docker 
  containers.
- The harness repository must be specified in the recipe
- Tests which reboot are not supported
- Tests which may want to spawn other containers are not supported 
- Running the test harness in a non-systemd distro is not tested
- Multi-host testing is not supported

To learn more about the above mentioned ksmeta variables, see :ref:`kickstart-metadata`.
