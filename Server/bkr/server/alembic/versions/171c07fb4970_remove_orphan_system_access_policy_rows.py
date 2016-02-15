# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""remove orphan system access policy rows

Revision ID: 171c07fb4970
Revises: 47af1e057a74
Create Date: 2015-05-19 13:37:02.807126

"""

# revision identifiers, used by Alembic.
revision = '171c07fb4970'
down_revision = '47af1e057a74'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    op.execute("""
        DELETE FROM system_access_policy_rule
        USING system_access_policy
        INNER JOIN system_access_policy_rule
            ON system_access_policy_rule.policy_id = system_access_policy.id
        WHERE NOT EXISTS
            (SELECT 1 FROM system WHERE custom_access_policy_id = system_access_policy.id)
        AND NOT EXISTS
            (SELECT 1 FROM system_pool WHERE access_policy_id = system_access_policy.id)
        """)
    op.execute("""
        DELETE FROM system_access_policy
        WHERE NOT EXISTS
            (SELECT 1 FROM system WHERE custom_access_policy_id = system_access_policy.id)
        AND NOT EXISTS
            (SELECT 1 FROM system_pool WHERE access_policy_id = system_access_policy.id)
        """)
def downgrade():
    pass # no downgrade because we are fixing up old data
