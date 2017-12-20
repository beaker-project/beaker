# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make recipe_task_param.recipe_task_id non-NULLable

Revision ID: 2384d43354a4
Revises: 4b0ed9e7e5b7
Create Date: 2017-12-20 16:16:55.678136
"""

# revision identifiers, used by Alembic.
revision = '2384d43354a4'
down_revision = '4b0ed9e7e5b7'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('recipe_task_param', 'recipe_task_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('recipe_task_param', 'recipe_task_id', existing_type=Integer, nullable=True)
