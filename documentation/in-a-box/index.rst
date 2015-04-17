.. _in-a-box:

Beaker in a box
===============

.. highlight:: console

Beaker in a box provides a way of using Vagrant and Ansible to install and configure
a complete working Beaker environment, including three virtual guests(VMs) to
act as test systems. This guide assumes that you already have Vagrant and Ansible
installed and working, also have a spare system capable of KVM virtualization
with at least 4GB of RAM running on Fedora 21.

Package Prerequisites 
---------------------

- vagrant
- vagrant-libvirt
- ansible

Cloning the beaker-in-a-box repo
--------------------------------

Start by cloning `Beaker-in-a-box's git
repository <http://git.beaker-project.org/cgit/~mjia/beaker-in-a-box/>`_::

    git clone git://git.beaker-project.org/beaker-in-a-box

Setting up Ansible
------------------

Ansible is connecting with remote machines over SSH, so we need to set up
passwordless ssh key authentication from your user to root on the host machine::

    ssh-copy-id root@localhost

Setting up libvirt and test systems
-----------------------------------

We will use Ansible to create a virtual network called beaker and three
test systems on your host system::

   ansible-playbook -i hosts setup_libvirt_and_virt.yml

.. note::

   Beaker in a box is using static IP and mac addresses. Please make sure that those
   static IP and mac addresses do not collide with any other machines on the same
   network. Those static IP and mac addresses can be found in group_vars/beaker.

Setting up Server and Lab controller 
------------------------------------

We will use Vagrant to set up a VM that acts as the server and the lab controller::

    vagrant up

This will start the VM and run the provisioning playbook. By default, Vagrant is
using centos-6 box as the base images of the VM, you can change it by modifying
the Vagrantfile file. For more information, refer to `Vagrant <https://docs.vagrantup.com/v2/>`_
documentation.

To be able to provision the test systems, passwordless login for the root user
is required to set up from the VM to your host system. First, ssh to the VM::

    vagrant ssh

Then run::

    ssh-copy-id root@192.168.120.1

Setup server to run job
-----------------------

We will now add a few task RPMS to ensure we can run jobs. Run this playbook on your host system
(assuming you have set your beaker client configuration successfully — running ``bkr whoami`` is
the easiest way to check that)::

    ansible-playbook -i hosts add_beaker_tasks.yml

If everything has completed successfully, now we are all set up and you should be
able to visit ``http://beaker-server-lc.beaker/bkr/`` from your host system's browser
and login as the admin user with password admin.
