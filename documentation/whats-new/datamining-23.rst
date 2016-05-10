Updating Your Data Mining Queries for Beaker 23
-----------------------------------------------

New ``installation`` database table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This release adds a new database table, ``installation``, which records each 
new installation of a distro on a system. The database upgrade process will 
populate this table with rows for all existing recipes. From this release 
onwards Beaker will create a new row in this table every time a system is 
provisioned, either for a recipe or manually (for example, on the system page).

This new table consolidates some existing fields that were previously spread 
across several different tables. If you are running SQL queries against the 
Beaker database directly, your queries may need to be updated. The schema 
changes are described in detail below.

The four timestamp columns on the ``recipe_resource`` table for recording 
installation progress (``rebooted``, ``install_started``, ``install_finished``, 
and ``postinstall_finished``) have been moved to the new ``installation`` 
table. You can join through the ``recipe`` table on ``installation.recipe_id``, 
for example::

    SELECT ..., installation.rebooted, ...
    FROM recipe_resource
    INNER JOIN recipe ON recipe_resource.recipe_id = recipe.id
    INNER JOIN installation ON installation.recipe_id = recipe.id
    ...

Similarly, the ``rendered_kickstart_id`` column on the ``recipe`` table has 
been moved to ``installation``.

On the ``command_queue`` table, the ``distro_tree_id`` and ``kernel_options`` 
columns are no longer used. Instead, new rows in ``command_queue`` are 
associated with an installation through the ``installation_id`` column and the 
distro tree and kernel options are stored there instead. Note that existing 
rows in ``command_queue`` may not have an associated installation, so your 
query should fall back to using ``command_queue.kernel_options`` if it needs to 
consider older rows. For example::

    SELECT ...,
        COALESCE(installation.kernel_options, command_queue.kernel_options),
        ...
    FROM activity
    INNER JOIN command_queue ON activity.id = command_queue.id
    LEFT JOIN installation ON command_queue.installation_id = installation.id
    WHERE activity.action = 'configure_netboot'
    ...
