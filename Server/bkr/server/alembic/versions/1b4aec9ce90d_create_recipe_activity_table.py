# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""create recipe activity table

Revision ID: 1b4aec9ce90d
Revises: 2173486573fe
Create Date: 2015-10-27 14:44:08.028198

"""

# revision identifiers, used by Alembic.
revision = '1b4aec9ce90d'
down_revision = '2173486573fe'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('recipe_activity',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recipe_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['activity.id'],
            name='recipe_activity_id_fk'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'],
            name='recipe_activity_recipe_id_fk'),
        mysql_engine='InnoDB'
    )

def downgrade():
    op.drop_table('recipe_activity')
