Installation
============

Pre-built Beaker packages are available from the `Download 
</beaker-project.org/download.html>`_ section of Beaker's web site. 
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
against MySQL, so it is recommended to use that.

First, make sure MySQL server is installed, and configure the daemon to run at 
startup::

    $ yum install -y mysql-server MySQL-python
    $ chkconfig mysqld on

For Unicode support in Beaker, it is recommended to configure MySQL to
store strings as UTF-8. This is controlled by the
``character-set-server`` option in ``/etc/my.cnf``::

    [mysqld]
    ...
    character-set-server=utf8

Now start the MySQL server::

    $ service mysqld start

Create a database, and grant access to a user. You can put the database
on the local machine, or on a remote machine.

::

    $ echo "create database <db_name> ;" | mysql
    $ echo "create user <user_name> ;" | mysql
    $ echo "grant all on <db_name>.* to <user_name> IDENTIFIED BY <password>;"| mysql

Update ``/etc/beaker/server.cfg`` with the details of the database::

    sqlalchemy.dburi = "mysql://<user_name>:<password>@<hostname>/<db_name>?charset=utf8"

Now let's initialise our DB with tables. We'll also create an admin
account called *admin* with password *testing*, and email
*root@localhost*.

::

    $ su apache -c 'beaker-init -u admin -p testing -e root@localhost'

Starting Beaker
~~~~~~~~~~~~~~~

We are now ready to start the Beaker service. First make sure Apache is on and 
configured to run on startup::

    $ chkconfig httpd on
    $ service httpd start

We need to switch SELinux off.

::

    $ setenforce 0

Due to permission issues, we need to delete the log file before we start
Beaker for the first time. Otherwise Beaker will not run properly.

::

    $ rm /var/log/beaker/server*.log
    $ rm /var/log/beaker/server*.lock

Start Beaker and configure it to run on startup.

::

    $ chkconfig beakerd on
    $ service beakerd start

To make sure Beaker is running go to http://localhost/bkr/ in your browser.

Adding a lab controller
-----------------------

Beaker uses lab controllers to manage the systems in its inventory. The lab 
controller serves files for network booting, monitors console logs, and 
executes fence commands to reboot systems. Typically the lab controller also 
provides DHCP and DNS services to the lab, but those services are not managed 
by Beaker.

In small Beaker installations, the lab controller can be the same system as the 
Beaker server.

Registering the lab controller
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To start with, we need to make Beaker aware of the new lab controller. Log in 
to Beaker using your administrator account create above, and select Admin → Lab 
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
   the default value ``http://localhost/bkr`` is adequate.

-  ``USERNAME``, ``PASSWORD``: The username and password which the lab
   controller will use when logging in to Beaker. This is the username
   and password you picked when registering the lab controller above.

Turn on Apache::

    $ chkconfig httpd on
    $ service httpd start

Turn on tftp::

    $ chkconfig xinetd on
    $ chkconfig tftp on
    $ service xinetd start

You can also use dnsmasq or any other TFTP server implementation. If
your TFTP server is configured to use a root directory other than the
default ``/var/lib/tftpboot`` you will need to set the ``TFTP_ROOT``
option in ``/etc/beaker/labcontroller.conf``.

The ``beaker-proxy`` daemon handles XML-RPC requests from within the lab
and proxies them to the server.

::

    $ chkconfig beaker-proxy on
    $ service beaker-proxy start

The ``beaker-watchdog`` daemon monitors systems and aborts their recipes
if they panic or exceed the time limit.

::

    $ chkconfig beaker-watchdog on
    $ service beaker-watchdog start

The ``beaker-provision`` daemon writes netboot configuration files in
the TFTP root directory and runs fence commands to reboot systems.

::

    $ chkconfig beaker-provision on
    $ service beaker-provision start

Beaker installs a configuration file into ``/etc/sudoers.d`` so that
beaker-proxy (running as apache) can clear the TFTP netboot files for
specific servers (owned by root). To ensure that Beaker lab controllers
read this directory, the following command must be enabled in
``/etc/sudoers`` (it is enabled by default in RHEL 6)::

    #includedir /etc/sudoers.d

Next steps
----------

You can now proceed to
:ref:`adding tasks <adding-tasks>`,
:ref:`importing distros <importing-distros>`,
:ref:`adding systems <adding-systems>`, and 
:ref:`running jobs <jobs>`.

There are two special tasks which Beaker relies on for normal operation: 
``/distribution/install`` and ``/distribution/reservesys``. You should add 
these to your Beaker installation before attempting to run jobs. You can build 
the tasks from source by cloning Beaker's git repository, or fetch a pre-built 
version of the tasks from http://beaker-project.org/tasks/.
