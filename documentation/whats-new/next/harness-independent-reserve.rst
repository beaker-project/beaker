Harness independent system reservation
======================================

A new XML element ``<reservesys>`` added to a recipe will reserve a
system after the tests have been completed. "An optional attribute,
``duration`` can be used to specify the time of the reservation in
seconds. By default it is 86400 seconds or 24 hours.


Unlike the ``/distribution/reservesys`` task (which is still fully supported),
this new mechanism reserves the system for the specified duration even
if the recipe execution is aborted by the external watchdog timer or
due to a kernel panic or installation failure.

Database upgrade:

Run ``beaker-init`` to create the table ``recipe_reservation``. 

Run the following SQL as well::

    ALTER TABLE recipe 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted', 'Reserved');
    ALTER TABLE recipe_task 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted', 'Reserved');
    ALTER TABLE recipe_set 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted', 'Reserved');
    ALTER  TABLE job 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted', 'Reserved');

Rollback instructions::

   DROP TABLE recipe_reservation;

   ALTER TABLE recipe 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted');
    ALTER TABLE recipe_task 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted');
    ALTER TABLE recipe_set 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted');
    ALTER  TABLE job 
       MODIFY status enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted');

(Contributed by Amit Saha in :issue:`639938`.)
