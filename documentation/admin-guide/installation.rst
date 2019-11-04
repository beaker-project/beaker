.. _install-guide:

Installation
============

Pre-built Beaker packages are available from the `Download
<../../download.html>`__ section of Beaker's web site.
There are two main repos. One containing packages needed for installing
the Beaker server and required components, another for packages needed
to run the Beaker client. Download the repo file that suits your requirements
and copy it to ``/etc/yum.repos.d``.


Installing the Beaker server
----------------------------

Start by installing the ``beaker-server`` package::

    $ yum install beaker-server

Preparing the database
~~~~~~~~~~~~~~~~~~~~~~

Beaker uses the `SQLAlchemy <http://www.sqlalchemy.org/>`_ database
library, which supports a large number of databases (including MySQL,
PostgreSQL, SQLite, Oracle, and Microsoft SQL Server) provided that a
suitable client driver is installed. However Beaker is only tested
against MariaDB, so it is recommended to use that.

First, make sure MariaDB server is installed, and configure the daemon to run at
startup::

    $ yum install -y mariadb-server MySQL-python
    $ systemctl enable mariadb

For Unicode support in Beaker, it is recommended to configure MariaDB to
store strings as UTF-8. This is controlled by the
``character-set-server`` option in ``/etc/my.cnf``::

    [mysqld]
    ...
    character-set-server=utf8

Now start the MySQL server::

    $ systemctl start mariadb

Create a database, and grant access to a user. You can put the database
on the local machine, or on a remote machine.

::

    $ echo "create database <db_name> ;" | mysql
    $ echo "create user <user_name> ;" | mysql
    $ echo "grant all on <db_name>.* to <user_name> IDENTIFIED BY '<password>';"| mysql

Update ``/etc/beaker/server.cfg`` with the details of the database::

    sqlalchemy.dburi = "mysql://<user_name>:<password>@<hostname>/<db_name>?charset=utf8"

.. todo::

   SQL Alchemy's parsing of dburi strings is changing in `SQL Alchemy 0.9
   <http://docs.sqlalchemy.org/en/rel_0_9/changelog/migration_09.html#the-password-portion-of-a-create-engine-no-longer-considers-the-sign-as-an-encoded-space>`__.
   Once we officially support a version of Fedora with SQL Alchemy 0.9+, we
   should make sure to advise users to use the appropriate formatting in the
   configuration file.

Now let's initialise our DB with tables. We'll also create an admin
account called *admin* with password *testing*, and email
*root@localhost*.

::

    $ beaker-init -u admin -p testing -e root@localhost

Starting Beaker
~~~~~~~~~~~~~~~

We are now ready to start the Beaker service. It is strongly recommended
that the Apache configuration be updated to serve Beaker over HTTPS rather
than HTTP.

First make sure Apache is on and configured to run on startup::

    $ systemctl enable httpd
    $ systemctl start httpd

We unfortunately need to switch SELinux off on the main Beaker server.

::

    $ setenforce 0

The appropriate port (80/443 for HTTP/HTTPS) must also be open in the
server firewall.

Start the Beaker scheduling daemon and configure it to run on startup.

::

    $ systemctl enable beakerd
    $ systemctl start beakerd

To make sure Beaker is running, open the URL configured in Apache in a
browser.


Adding a lab controller
-----------------------

Beaker uses lab controllers to manage the systems in its inventory. The lab
controller serves files for network booting, monitors console logs, and
executes fence commands to reboot systems.

In small Beaker installations, the lab controller can be the same system as the
Beaker server.


External services
~~~~~~~~~~~~~~~~~

Beaker expects DHCP, DNS, and NTP services to be available in the lab, with
the appropriate TFTP, DNS and NTP details provided to test systems by the
DHCP server.

The TFTP service must run directly on the lab controller to allow Beaker
to correctly provision test systems. The DHCP, DNS and NTP services *may*
be run on the lab controller, but do not need to be.

A serial console server is also a useful addition to the lab configuration
(as it can provide useful diagnostic information for failure, and allows
Beaker to monitor the console log for kernel panics), but Beaker will
operate correctly without one.


Registering the lab controller
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To start with, we need to make Beaker aware of the new lab controller. Log in
to Beaker using your administrator account created above, and select Admin → Lab
Controllers from the menu. Click "Add ( + )" to add a new lab controller.

The new lab controller form requires the following fields:

-  *FQDN*: This is the fully qualified domain name of the lab
   controller.

-  *Username*: This is the login name that the lab controller will use
   to login to beaker. Because this is a machine account we recommend
   prepending it with host/, so for example
   host/lab\_controller.example.com

-  *Password*: This is the password that goes along with the username,
   again we will use: *testing*

-  *Lab Controller Email Address*: All user accounts require a unique
   email address, you can use root@FQDN of lab controller.

Save the form and we are done with the server side for now.


Configuring the lab controller
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install the lab controller package::

    $ yum install beaker-lab-controller

Settings for the lab controller daemons are in
``/etc/beaker/labcontroller.conf``. At a minimum you will need to change
the following settings:

-  ``HUB_URL``: The URL of your Beaker server *without the trailing
   slash*. If the lab controller and server are the same machine then
   the default value ``https://localhost/bkr`` is adequate.

-  ``USERNAME``, ``PASSWORD``: The username and password which the lab
   controller will use when logging in to Beaker. This is the username
   and password you picked when registering the lab controller above.

Turn on Apache::

    $ systemctl enable httpd
    $ systemctl start httpd


.. _archive-server:

By default, Beaker stores log files for jobs locally on the lab controller
and publishes them through Apache. The ``beaker-transfer`` daemon can be
configured to move log files for completed recipes to a separate archive
server. The relevant settings to configure this are described in
``/etc/beaker/labcontroller.conf``.

Turn on tftp::

    $ systemctl enable xinetd
    $ systemctl enable tftp
    $ systemctl start xinetd

You can also use dnsmasq or any other TFTP server implementation. If
your TFTP server is configured to use a root directory other than the
default ``/var/lib/tftpboot`` you will need to set the ``TFTP_ROOT``
option in ``/etc/beaker/labcontroller.conf``.

The ``beaker-proxy`` daemon handles XML-RPC requests from within the lab
and proxies them to the server.

::

    $ systemctl enable beaker-proxy
    $ systemctl start beaker-proxy

The ``beaker-watchdog`` daemon monitors systems and aborts their recipes
if they panic or exceed the time limit.

::

    $ systemctl enable beaker-watchdog
    $ systemctl start beaker-watchdog

The ``beaker-provision`` daemon writes netboot configuration files in
the TFTP root directory and runs fence commands to reboot systems.

::

    $ systemctl enable beaker-provision
    $ systemctl start beaker-provision

Beaker installs a configuration file into ``/etc/sudoers.d`` so that
beaker-proxy (running as apache) can clear the TFTP netboot files for
specific servers (owned by root). To ensure that Beaker lab controllers
read this directory, the following command must be enabled in
``/etc/sudoers`` (it is enabled by default from RHEL 6 forward)::

    #includedir /etc/sudoers.d

The appropriate ports (80/443 for HTTP/HTTPS access to log files through
Apache, 8000 for test system access to beaker-proxy and 69 for TFTP) must
also be open in the lab controller firewall.

.. todo::

   Document console server integration, see
   https://bugzilla.redhat.com/show_bug.cgi?id=1029737


Adding the core Beaker tasks
----------------------------

There are a number of `standard tasks
<../../../docs/user-guide/beaker-provided-tasks.html>`__ that are expected
to be available in every Beaker installation. You should add
these to your Beaker installation before attempting to run jobs.

You can build and upload most of the tasks from source by cloning the
`beaker-core-tasks git repository
<https://github.com/beaker-project/beaker-core-tasks/>`__, or fetch a
pre-built version of the tasks as RPMs from `beaker-project.org
<https://beaker-project.org/tasks/>`__.

The guest recipe related ``/distribution/virt/*`` tasks are currently only
available as pre-built RPMs.


.. _sync-tasks:

Copying the tasks from an existing Beaker installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Alternatively, you can copy *all* the tasks from another Beaker instance
using the ``beaker-sync-tasks`` tool (distributed as a part of the
``beaker-server`` package and first available with the 0.12
release). For example::

    $ beaker-sync-tasks --remote=https://server1.com

The above command will copy all the tasks, including the standard tasks,
from the Beaker instance at ``http://server1.com`` to the local instance.
If there are tasks having the same name in the local Beaker instance, they
will be overwritten only if the versions are different.

By default, the script asks for your approval before beginning the
task upload. If that is not suitable for your purpose, you may specify
a :option:`--force <beaker-sync-tasks --force>` switch so that the script may run without any user
intervention. The :option:`--debug <beaker-sync-tasks --debug>` switch turns on verbose logging
messages on the standard output.


.. _next-steps:

Next steps
----------

You can now proceed to
:ref:`adding tasks <adding-tasks>`,
:ref:`importing distros <importing-distros>`,
:ref:`adding systems <adding-systems>`, and
:ref:`running jobs <jobs>`.
