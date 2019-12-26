.. _in-a-box:

Beaker in a box
===============

.. highlight:: console

Beaker in a box provides a way of using Ansible to install and configure a
complete working Beaker environment, including three virtual guests(VMs) to act
as test systems. This guide assumes that you already have Ansible installed and
working, also have a spare system capable of KVM virtualization with at least
4GB of RAM running on Fedora 30.

Package Prerequisites
---------------------

- ansible >= 2.5

Cloning the beaker-in-a-box repo
--------------------------------

Start by cloning `Beaker-in-a-box's git
repository <https://github.com/beaker-project/beaker-in-a-box/>`_::

    git clone https://github.com/beaker-project/beaker-in-a-box.git

Setting up Beaker
-----------------

The playbook sets the entire environment in several steps:

#. Defines virtual machines and a virtual network called ``beaker``.

#. Provisions the server and the lab controller as one virtual machine. SSH Keys
   between host and virtual machine are exchanged to easy access and control of
   test systems using ``virsh``. Default root password used is ``beaker``.

#. Provisions the test machines and adds them as available resources to the lab controller/server.

Start the setup using Ansible by running::

   ansible-playbook setup_beaker.yml --ask-become-pass

.. note::

   Beaker in a box is using static IP and mac addresses. Please make sure that those
   static IP and mac addresses do not collide with any other machines on the same
   network. Those static IP and mac addresses can be found in group_vars/beaker.

Customizing the provisioning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default the server and lab controller VM is provisioned from a CentOS 7 HTTP
URL. If you prefer to provision it from a different HTTP URL, run the playbook
by passing `variables on the command line
<http://docs.ansible.com/ansible/playbooks_variables.html#passing-variables-on-the-command-line>`_
which will overwrite the default.

For example, create a new YAML file ``extravars.yml``::

  ---
  netinstall_url: http://mirror.centos.org/centos/7/os/x86_64/
  kickstart_repos:
    updates: http://mirror.centos.org/centos/7/updates/x86_64/

It provides the netinstall URL and additional repositories the VM is provisioned
with. Then run the playbook and include the file to the ``ansible-playbook``
command::

  ansible-playbook setup_beaker.yml --ask-become-pass -e@extravars.yml

In the same fashion, you can add additional distros during the provisioning
process by setting the ``user_distros`` variable. To illustrate this, here is an
example::

  ---
  user_distros:
    - http://mirror.centos.org/centos/6.8/os/x86_64/

This will add CentOS 6.8 as an additional distribution, among the ones already
added by default, to provision test machines from.

Verifying the server installation
---------------------------------

All the virtual machines should be configured at this point.

Visiting `http://beaker-server-lc.beaker/bkr/
<http://beaker-server-lc.beaker/bkr/>`_ from your host systems's browser should
show the beaker systems page. The Ansible playbook created an administrator user
for us. Both the username and password are ``admin``.

Now that you've logged into the web interface, it's time to schedule a job. An
easy way to schedule a job is by performing a system scan for one of your test
systems. On the systems page, click on a system and navigate to the
:guilabel:`Details` tab. Schedule a scan by clicking on the :guilabel:`Scan`
button.

The robust web interface exposes many of Beakers features and is easy to work
with. Beaker also provides several CLI tools to manage your Beaker setup. Attempt
to ssh into the Beaker server to access the tools directly::

   ssh root@beaker-server-lc.beaker -i ~/.ssh/id_rsa

.. note::

   Remember, the default root password on the Beaker server is ``beaker``.

Or you can install and configure the :program:`bkr` client to use your local
Beaker server (see :ref:`installing-bkr-client`). After installing and configuring
the client on your local workstation, run ``bkr whoami`` through the client to
check that is working.

Next steps
----------

The playbook has already taken care of adding tasks, importing distros and
adding systems, but for completeness we recommend reading the next sections to
get a better understanding by proceeding to
:ref:`adding tasks <adding-tasks>`,
:ref:`importing distros <importing-distros>`,
:ref:`adding systems <adding-systems>`, and
:ref:`running jobs <jobs>`.
