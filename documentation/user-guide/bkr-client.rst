
.. _bkr-client:

The ``bkr`` command-line client
===============================

Supported platforms
-------------------

The Beaker command line client is fully supported on recent versions of
Fedora and on Red Hat Enterprise Linux 6. Most commands are also supported
on Red Hat Enterprise Linux 5 (when this is not the case, it will be noted
in the documentation of the affected command by indicating the minimum
required version of Python).


.. _installing-bkr-client:

Installing and configuring the client
-------------------------------------

Pre-built Beaker packages are available from the `Download 
<../../download.html>`_ section of Beaker's web site. Download 
the repo file that suits your requirements and copy it to ``/etc/yum.repos.d``.

Install the ``beaker-client`` package::

    $ sudo yum install beaker-client

A sample configuration is installed as 
``/usr/share/doc/beaker-client-*/client.conf.example``. Copy it to 
``/etc/beaker/client.conf`` or ``~/.beaker_client/config`` and edit it there.

First, set the URL of your Beaker server *without* trailing slash::

    HUB_URL = "http://mybeaker.example.com/bkr"

You'll then need to configure how your Beaker client authenticates with
the Beaker server. You can use either password authentication, or
Kerberos authentication. For password authentication, add the following::

    AUTH_METHOD = "password"
    USERNAME = "username"
    PASSWORD = "password"

If instead Kerberos authentication is preferred::

    AUTH_METHOD = "krbv"
    KRB_REALM = "REALM.EXAMPLE.COM"

To verify it is working properly::

    $ bkr whoami

It should print your username.

Using the client
----------------

For full details about the ``bkr`` client and its subcommands, refer to the 
:ref:`Beaker client man pages <man>`. A summary of some common commands is 
given below.

To create a simple Job workflow, the beaker client comes with the
command ``bkr workflow-simple``. This simple Job workflow will create
the XML for you from various options passed at the shell prompt, and
submit this to the Beaker server. To see all the options that can be
passed during invocation of ``workflow-simple``, use the following
command::

    $ bkr workflow-simple --help

A common set of parameters that may be passed to the workflow-simple
options would be the following::

    $ bkr workflow-simple --username=<user> --password=<passwd> --dryrun \
        --arch=<arch> --distro=<distro_name> --task=<task_name> \
        --type=<TYPE> --whiteboard=<whiteboard_name> --debug > my_job.xml

To submit an existing Job workflow::

    $ bkr job-submit job_xml

If successful, you will be shown the Job ID and the progress of your Job.

To watch a Job::

    $ bkr job-watch J:job_id

To cancel a Job you have created::

    $ bkr job-cancel J:job_id

To show all Tasks available for a given distro::

    $ bkr task-list distro

To add a Task::

    $ bkr task-add task_rpm
