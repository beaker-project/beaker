# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Migrate from 0.12 to 0.13

Revision ID: 41aa3372239e
Revises: 442672570b8f
Create Date: 2014-10-09 12:55:52.303985

"""

# revision identifiers, used by Alembic.
revision = '41aa3372239e'
down_revision = '442672570b8f'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("""
        ALTER TABLE tg_group
            MODIFY group_name VARCHAR(16) NOT NULL,
            ADD COLUMN ldap BOOLEAN NOT NULL DEFAULT 0,
            ADD INDEX (ldap),
            ADD COLUMN root_password VARCHAR(255) AFTER display_name
        """)
    op.add_column('user_group', sa.Column('is_owner', sa.Boolean,
            nullable=False))
    op.execute("""
        ALTER TABLE job
        ADD COLUMN group_id int(11) default NULL AFTER owner_id,
        ADD CONSTRAINT `job_group_id_fk` FOREIGN KEY (group_id)
            REFERENCES `tg_group` (group_id),
        ADD INDEX (status),
        ADD INDEX (result)
        """)
    op.execute("""
        ALTER TABLE recipe_set
        ADD INDEX (status),
        ADD INDEX (result),
        ADD INDEX (priority)
        """)
    op.execute("""
        ALTER TABLE recipe
        ADD INDEX (status),
        ADD INDEX (result)
        """)
    op.execute("""
        DELETE FROM system_status_duration
        USING system_status_duration
        LEFT JOIN (
            SELECT system_id, MAX(start_time) start_time
            FROM system_status_duration
            GROUP BY system_id) x
            ON system_status_duration.system_id = x.system_id
                AND system_status_duration.start_time = x.start_time
        WHERE finish_time IS NULL
            AND x.start_time IS NULL
        """)

def downgrade():
    op.execute("""
        ALTER TABLE tg_group
            MODIFY group_name VARCHAR(16) DEFAULT NULL,
            DROP COLUMN ldap,
            DROP COLUMN root_password
        """)
    op.drop_column('user_group', 'is_owner')
    op.execute("""
        ALTER TABLE job
        DROP FOREIGN KEY job_group_id_fk,
        DROP COLUMN group_id,
        DROP INDEX status,
        DROP INDEX result
        """)
    op.execute("""
        ALTER TABLE recipe_set
        DROP INDEX status,
        DROP INDEX result,
        DROP INDEX priority
        """)
    op.execute("""
        ALTER TABLE recipe
        DROP INDEX status,
        DROP INDEX result
        """)
