# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Migrate from 0.15 to 0.16

Revision ID: 2f38ab976d17
Revises: 49a4a1e3779a
Create Date: 2014-10-09 11:01:11.778636

"""

# revision identifiers, used by Alembic.
revision = '2f38ab976d17'
down_revision = '49a4a1e3779a'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import add_enum_value, drop_enum_value, \
    drop_fk, drop_index

def upgrade():
    op.execute("""
        ALTER TABLE recipe_task
        ADD name VARCHAR(255) NOT NULL AFTER recipe_id,
        ADD version VARCHAR(255) AFTER name,
        ADD fetch_url VARCHAR(2048) AFTER version,
        ADD fetch_subdir VARCHAR(2048) NOT NULL DEFAULT '' AFTER fetch_url,
        MODIFY task_id INT,
        ADD INDEX (name),
        ADD INDEX (version),
        ADD INDEX (name, version)
        """)
    op.execute("""
        UPDATE recipe_task
        SET name = (SELECT name FROM task WHERE id = recipe_task.task_id)
        """)
    add_enum_value('system_access_policy_rule', 'permission', 'view', nullable=True)
    op.execute("""
        INSERT INTO system_access_policy (system_id)
        SELECT id FROM system
        WHERE NOT EXISTS (SELECT 1 FROM system_access_policy
            WHERE system_id = system.id)
        """)
    op.execute("""
        INSERT INTO system_access_policy_rule
            (policy_id, user_id, group_id, permission)
        SELECT system_access_policy.id, NULL, NULL, 'view'
        FROM system_access_policy
        INNER JOIN system ON system_access_policy.system_id = system.id
        WHERE NOT EXISTS (SELECT 1 FROM system_access_policy_rule
            WHERE policy_id = system_access_policy.id
                AND user_id IS NULL
                AND group_id IS NULL
                AND permission = 'view')
            AND system.private = 0
        """)
    op.add_column('command_queue', sa.Column('quiescent_period', sa.Integer))
    op.create_index('status', 'command_queue', ['status'])
    op.add_column('power', sa.Column('power_quiescent_period', sa.Integer, nullable=False))
    op.execute("UPDATE power SET power_quiescent_period = 5")
    op.alter_column('tg_user', 'password', type_=sa.UnicodeText())
    op.execute("ALTER TABLE beaker_tag DROP PRIMARY KEY, ADD PRIMARY KEY (id)")
    # These tables were never used for anything, so they really can be safely dropped.
    op.drop_table('locked')
    op.drop_table('serial')
    op.drop_table('serial_type')
    op.drop_table('install')

def downgrade():
    drop_fk('recipe_task', ['task_id'])
    op.execute("""
        ALTER TABLE recipe_task
        DROP name,
        DROP version,
        DROP fetch_url,
        DROP fetch_subdir,
        MODIFY task_id INT NOT NULL
        """)
    op.create_foreign_key(None, 'recipe_task', 'task',
                ['task_id'], ['id'])
    op.execute("DELETE FROM system_access_policy_rule WHERE permission = 'view'")
    drop_enum_value('system_access_policy_rule', 'permission', 'view', nullable=False)
    op.drop_column('command_queue', 'quiescent_period')
    drop_index('command_queue', ['status'])
    op.drop_column('power', 'power_quiescent_period')
    op.alter_column('tg_user', 'password', type_=sa.Unicode(40))
    op.execute("ALTER TABLE beaker_tag DROP PRIMARY KEY, ADD PRIMARY KEY (id, tag)")
    op.create_table('locked', sa.Column('id', sa.Integer(), primary_key=True))
    op.create_table('serial', sa.Column('id', sa.Integer(), primary_key=True))
    op.create_table('serial_type', sa.Column('id', sa.Integer(), primary_key=True))
    op.create_table('install', sa.Column('id', sa.Integer(), primary_key=True))
