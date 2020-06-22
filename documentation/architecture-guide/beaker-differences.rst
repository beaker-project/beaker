How is Beaker different to …?
=============================

In a world of Continious Integration (CI), Beaker's capabilities seem to look as
yet another system for testing. Beaker however comes with its own unique feature
set aimed at lab automation and testing using bare metal hardware. This will
give a quick overview of differences to similar-looking solutions.

Jenkins
-------

Red Hat created Beaker to test operating systems and their integration with the
underlying hardware, even on pre-release hardware that is potentially unstable.
For this, Beaker has built-in capabilities for detecting hardware lock ups (see
:ref:`watchdog-timer-capability`) or installation failures (see
:ref:`job-monitoring`). Jenkins - formerly called Hudson - was originally
intended for testing (Java based) applications. Its capabilities to provision
hardware for testing are limited, since the main assumption is that all attached
nodes are already provisioned, with a working operating system.

OpenStack
---------

OpenStack is an on-premise cloud. In order to provide a simple API to consumers,
OpenStack tries to abstract the details of the underlying bare metal as much as
possible. Beaker, on the other hand, exposes as much detail as possible about
the underlying hardware, so that users can write hardware-specific tests.

Foreman
-------

Foreman and Beaker cover different use cases. Foreman's focus is on long-lived
production machines. It has sophisticated support for provisioning them and
managing them after they are provisioned. Beaker, on the other hand, provisions
systems for short-lived testing purposes.
