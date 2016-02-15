# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Clear removed users from groups

Revision ID: 2091c783bda6
Revises: b830bfac525
Create Date: 2015-12-01 15:40:16.063518
"""

# revision identifiers, used by Alembic.
revision = '2091c783bda6'
down_revision = 'b830bfac525'

import logging
from alembic import op
from sqlalchemy.sql import text

log = logging.getLogger(__name__)

def upgrade():
    # Unfortunately we need to loop over removed users in Python land, because 
    # there is no way to do the necessary two-step insertion into activity and 
    # group_activity using just bulk INSERT...SELECT statements.
    connection = op.get_bind()
    rows = connection.execute("""
        SELECT tg_group.group_id, tg_user.user_id, tg_user.user_name
        FROM tg_group
        INNER JOIN user_group ON tg_group.group_id = user_group.group_id
        INNER JOIN tg_user ON tg_user.user_id = user_group.user_id
        WHERE tg_user.removed IS NOT NULL
        """)
    activity_insert = text("""
        INSERT INTO activity (user_id, created, type, service, field_name, action, old_value)
        VALUES ((SELECT MIN(user_id) FROM tg_user), UTC_TIMESTAMP(), 'group_activity', 'Migration', 'User', 'Removed', :user_name)
        """)
    group_activity_insert = text("""
        INSERT INTO group_activity (id, group_id)
        VALUES (:activity_id, :group_id)
        """)
    user_group_delete = text("""
        DELETE FROM user_group
        WHERE user_id = :user_id AND group_id = :group_id
        """)
    for group_id, user_id, user_name in rows:
        log.debug('Clearing user %s from group %s', user_name, group_id)
        result = connection.execute(activity_insert, user_name=user_name)
        activity_id = result.lastrowid
        connection.execute(group_activity_insert, activity_id=activity_id, group_id=group_id)
        connection.execute(user_group_delete, user_id=user_id, group_id=group_id)

def downgrade():
    # no downgrade because we are just fixing up old data
    pass
