# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make recipe_activity.recipe_id non-NULLable

Revision ID: 4957d4804ba
Revises: 5ab66e956c6b
Create Date: 2017-12-20 16:04:56.429524
"""

# revision identifiers, used by Alembic.
revision = '4957d4804ba'
down_revision = '5ab66e956c6b'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('recipe_activity', 'recipe_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('recipe_activity', 'recipe_id', existing_type=Integer, nullable=True)
