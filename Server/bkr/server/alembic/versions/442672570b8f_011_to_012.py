# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Migrate from 0.11 to 0.12

Revision ID: 442672570b8f
Revises: None
Create Date: 2014-10-09 13:14:34.764620

"""

# revision identifiers, used by Alembic.
revision = '442672570b8f'
down_revision = None

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import add_enum_value, drop_enum_value

def upgrade():
    op.execute("""
        ALTER TABLE job
        ADD COLUMN dirty_version BINARY(16) NOT NULL AFTER id,
        ADD COLUMN clean_version BINARY(16) NOT NULL AFTER dirty_version,
        ADD INDEX ix_job_dirty_clean_version (dirty_version, clean_version)
        """)
    op.execute("UPDATE job SET dirty_version = '1111111111111111'")
    op.add_column('system', sa.Column('loan_comment', sa.Unicode(1000)))
    op.create_table('disk',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('system_id', sa.Integer, sa.ForeignKey('system.id'),
            nullable=False),
        sa.Column('model', sa.Unicode(255)),
        sa.Column('size', sa.BigInteger),
        sa.Column('sector_size', sa.Integer),
        sa.Column('phys_sector_size', sa.Integer),
        mysql_engine='InnoDB'
    )
    op.execute("""
        DELETE FROM task USING task, task AS vtask
            WHERE task.id < vtask.id AND task.name = vtask.name
        """)
    op.alter_column('task', 'name', type_=sa.Unicode(255))
    op.create_unique_constraint('name', 'task', ['name'])
    add_enum_value('job', 'result', 'None', nullable=False)
    add_enum_value('recipe_set', 'result', 'None', nullable=False)
    add_enum_value('recipe', 'result', 'None', nullable=False)
    add_enum_value('recipe_task', 'result', 'None', nullable=False)
    add_enum_value('recipe_task_result', 'result', 'None', nullable=False)

def downgrade():
    op.execute("ALTER TABLE job DROP COLUMN dirty_version, DROP COLUMN clean_version")
    op.drop_column('system', 'loan_comment')
    op.drop_table('disk')
    op.drop_index('name', 'task')
    op.alter_column('task', 'name', type_=sa.Unicode(2048))
    drop_enum_value('job', 'result', 'None', nullable=False)
    drop_enum_value('recipe_set', 'result', 'None', nullable=False)
    drop_enum_value('recipe', 'result', 'None', nullable=False)
    drop_enum_value('recipe_task', 'result', 'None', nullable=False)
    drop_enum_value('recipe_task_result', 'result', 'None', nullable=False)
