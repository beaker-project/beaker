.. _atomic-host:

Running tests on an Atomic host
-------------------------------

.. versionadded:: 0.18.3

Beaker supports running tests on host operating systems based on the 
`Project Atomic <https://projectatomic.io>`__ pattern. The tests are run in a Docker
container instead of the host when such an OS is used. If you are not familiar
with this Beaker feature, see :ref:`tests-in-container` to learn more. Familiarity
with this feature is assumed for the rest of this guide.

An example recipe which uses an atomic host OS is as follows:

.. literalinclude:: contained-test-harness-atomic.xml

The above recipe specifies that the test harness should be run in a CentOS 7 
container. Two additional ksmeta variables have to be specified:

- ``ostree_repo_url``: This variable is used to specify the ``rpm-ostree`` repository
- ``ostree_ref``: This variable is used to specify the ``rpm-ostree`` remote ref

.. note::

   You may also note that the above recipe specifies ``<memory op="&gt;" value="1500"/>``
   in the ``<hostRequires>``. This is to specify that we want the host system to have
   at least 1500 MB memory. You may or may not need this to successfully execute a 
   recipe.

