Group password ("feature")
==============

Group owners can set a password on their group. The password is used as the
root password on systems provisioned by a recipe with an associated job group.

Run the following SQL:

    ALTER TABLE tg_group ADD COLUMN password VARCHAR(255) AFTER display_name;

To rollback:

    ALTER TABLE tg_group DROP COLUMN password;
