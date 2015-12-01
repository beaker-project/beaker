# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Clear removed users from system access policies

Revision ID: 362bb6508a2b
Revises: 2091c783bda6
Create Date: 2015-12-01 16:35:35.653412
"""

# revision identifiers, used by Alembic.
revision = '362bb6508a2b'
down_revision = '2091c783bda6'

import logging
from alembic import op
from sqlalchemy.sql import text

log = logging.getLogger(__name__)

def upgrade():
    # Unfortunately we need to loop over removed users in Python land, because 
    # there is no way to do the necessary two-step insertion into activity and 
    # system_activity/system_pool_activity using just bulk INSERT...SELECT 
    # statements.
    activity_insert = text("""
        INSERT INTO activity (user_id, created, type, service, field_name, action, old_value)
        VALUES ((SELECT MIN(user_id) FROM tg_user), UTC_TIMESTAMP(), :activity_type,
                'Migration', 'Access Policy Rule', 'Removed', :old_value)
        """)
    system_activity_insert = text("""
        INSERT INTO system_activity (id, system_id)
        VALUES (:activity_id, :system_id)
        """)
    system_pool_activity_insert = text("""
        INSERT INTO system_pool_activity (id, pool_id)
        VALUES (:activity_id, :pool_id)
        """)
    rule_delete = text("""
        DELETE FROM system_access_policy_rule
        WHERE id = :rule_id
        """)
    connection = op.get_bind()
    rows = connection.execute("""
        SELECT system_access_policy_rule.id, permission, tg_user.user_name, system.id
        FROM system_access_policy_rule
        INNER JOIN system_access_policy ON system_access_policy_rule.policy_id = system_access_policy.id
        INNER JOIN system ON system.custom_access_policy_id = system_access_policy.id
        INNER JOIN tg_user ON tg_user.user_id = system_access_policy_rule.user_id
        WHERE tg_user.removed IS NOT NULL
        """)
    for rule_id, permission, user_name, system_id in rows:
        log.debug('Clearing user %s from system %s access policy', user_name, system_id)
        old_value = u'<grant %s to %s>' % (permission, user_name)
        result = connection.execute(activity_insert,
                activity_type=u'system_activity', old_value=old_value)
        activity_id = result.lastrowid
        connection.execute(system_activity_insert,
                activity_id=activity_id, system_id=system_id)
        connection.execute(rule_delete, rule_id=rule_id)
    rows = connection.execute("""
        SELECT system_access_policy_rule.id, permission, tg_user.user_name, system_pool.id
        FROM system_access_policy_rule
        INNER JOIN system_access_policy ON system_access_policy_rule.policy_id = system_access_policy.id
        INNER JOIN system_pool ON system_pool.access_policy_id = system_access_policy.id
        INNER JOIN tg_user ON tg_user.user_id = system_access_policy_rule.user_id
        WHERE tg_user.removed IS NOT NULL
        """)
    for rule_id, permission, user_name, pool_id in rows:
        log.debug('Clearing user %s from pool %s access policy', user_name, pool_id)
        old_value = u'<grant %s to %s>' % (permission, user_name)
        result = connection.execute(activity_insert,
                activity_type=u'system_pool_activity', old_value=old_value)
        activity_id = result.lastrowid
        connection.execute(system_pool_activity_insert,
                activity_id=activity_id, pool_id=pool_id)
        connection.execute(rule_delete, rule_id=rule_id)

def downgrade():
    # no downgrade because we are just fixing up old data
    pass
