# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make recipe_task_result.recipe_task_id non-NULLable

Revision ID: 21330bf93a75
Revises: 46b19cc8fd7e
Create Date: 2017-12-20 16:40:20.679490
"""

# revision identifiers, used by Alembic.
revision = '21330bf93a75'
down_revision = '46b19cc8fd7e'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('recipe_task_result', 'recipe_task_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('recipe_task_result', 'recipe_task_id', existing_type=Integer, nullable=True)
