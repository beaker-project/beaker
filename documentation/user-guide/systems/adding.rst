
.. _adding-systems:

Adding your system to Beaker
============================

To add a system, go to any system search page, then click the :guilabel:`Add` 
button at the bottom of the page. After filling in the system's details, click 
the :guilabel:`Save Changes` button.

You will then need to update the Power details. To test they work, try hitting 
the power action buttons to ensure the system is responding correctly. The Arch 
details should then be updated, and then update the Install options with 
``console=ttyS1,115200n8 ksdevice=link`` for each arch. See 
:ref:`system-details-tabs`. You'll need to ensure that your System is hooked up 
to the conserver. Try provisioning a system (see :ref:`provisioning-a-system`). 
You can watch the provisioning process through the console. Please, be patient. 
The provisioning may take some time.

Once the System has been added, you should :ref:`create a job
<submitting-a-new-job>` to run the Beaker-provided :ref:`inventory-task` task
on the machine.  The easiest way to do this is to use the ``machine-test``
workflow to generate and submit an appropriate job definition::

    bkr machine-test --inventory --family=RedHatEnterpriseLinux6 \
         --arch=x86_64 --machine=<FQDN>

Refer to :ref:`bkr-machine-test` for more details.
