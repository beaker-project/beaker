# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Convert system groups to system pools

Revision ID: 1c444555ea3d
Revises: da9939e1007
Create Date: 2015-02-24 10:34:00.154380

"""

# revision identifiers, used by Alembic.
revision = '1c444555ea3d'
down_revision = 'da9939e1007'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('system_pool',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(length=255), nullable=False),
    sa.Column('description', sa.Unicode(length=4000), nullable=True),
    sa.Column('owning_group_id', sa.Integer(), nullable=True),
    sa.Column('owning_user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['owning_group_id'], ['tg_group.group_id'], ),
    sa.ForeignKeyConstraint(['owning_user_id'], ['tg_user.user_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    mysql_engine='InnoDB'
    )
    op.create_table('system_pool_activity',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('pool_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['activity.id'], ),
    sa.ForeignKeyConstraint(['pool_id'], ['system_pool.id'], ),
    sa.PrimaryKeyConstraint('id'),
    mysql_engine='InnoDB'
    )
    op.create_table('system_pool_map',
    sa.Column('system_id', sa.Integer(), nullable=False),
    sa.Column('pool_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['pool_id'], ['system_pool.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['system_id'], ['system.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('system_id', 'pool_id'),
    mysql_engine='InnoDB'
    )

    # create system pools
    op.execute("""
    INSERT INTO system_pool (name, description, owning_group_id)
    SELECT tg_group.group_name, CONCAT('Pool migrated from group ', tg_group.group_name), tg_group.group_id
    FROM tg_group
    WHERE EXISTS (SELECT 1 FROM system_group WHERE system_group.group_id = tg_group.group_id);
    """)

    # Update system pool and system mappings
    op.execute("""
    INSERT INTO system_pool_map(system_id, pool_id)
       SELECT system_group.system_id, system_pool.id FROM system_group
       INNER JOIN tg_group ON system_group.group_id = tg_group.group_id
       INNER JOIN system_pool ON system_pool.name = tg_group.group_name
    """)

    # Create activity records
    op.execute("""
    INSERT INTO activity (user_id, created, type, field_name, service, action, new_value)
    SELECT (SELECT MIN(user_id) FROM tg_user), UTC_TIMESTAMP(), 'system_pool_activity', 'Pool', 'Migration','Created', name
    FROM system_pool;
    """)

    # Create system_pool_activity records
    op.execute("""
    INSERT INTO system_pool_activity (id, pool_id)
    SELECT activity.id, system_pool.id FROM activity
    INNER JOIN system_pool ON
    activity.action='Created' AND activity.new_value=system_pool.name;
    """)

def downgrade():
    op.drop_table('system_pool_map')
    op.execute("""
    DELETE FROM system_pool_activity;
    DELETE FROM activity WHERE type='system_pool_activity';
    """)
    op.drop_table('system_pool_activity')
    op.drop_table('system_pool')
