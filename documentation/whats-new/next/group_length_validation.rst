Group name length changes
-------------------------

The maximum group name length has now been increased to 255 characters
from 16 characters.

Please run the following SQL::

    ALTER TABLE tg_group MODIFY group_name VARCHAR(255);

To rollback::

    ALTER TABLE tg_group MODIFY group_name VARCHAR(16);

Validation has also been added to the the XML-RPC interface so
that it reports an appropriate error message when the specified name
exceeds the limit.

(Contributed by Amit Saha in :issue:`990349`)
