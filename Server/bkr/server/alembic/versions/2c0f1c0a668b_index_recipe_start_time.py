# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Index recipe.start_time

Revision ID: 2c0f1c0a668b
Revises: 3fc28d7eb6d3
Create Date: 2014-10-10 11:24:56.207992

"""

# revision identifiers, used by Alembic.
revision = '2c0f1c0a668b'
down_revision = '3fc28d7eb6d3'

from alembic import op
import sqlalchemy as sa

def upgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('recipe')
    if not any(index['column_names'] == ['start_time'] for index in indexes):
        op.create_index('ix_recipe_start_time', 'recipe', ['start_time'])

def downgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('recipe')
    if any(index['name'] == 'ix_recipe_start_time' for index in indexes):
        op.drop_index('ix_recipe_start_time', 'recipe')
