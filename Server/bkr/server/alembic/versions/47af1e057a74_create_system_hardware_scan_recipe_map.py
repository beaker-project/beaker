# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Create system_hardware_scan_recipe_map

Revision ID: 47af1e057a74
Revises: 19d89d5fbde6
Create Date: 2015-05-12 12:20:58.644650

"""

# revision identifiers, used by Alembic.
revision = '47af1e057a74'
down_revision = '19d89d5fbde6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('system_hardware_scan_recipe_map',
    sa.Column('system_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['system_id'], ['system.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('system_id', 'recipe_id'),
    mysql_engine='InnoDB')

def downgrade():
    op.drop_table('system_hardware_scan_recipe_map')
