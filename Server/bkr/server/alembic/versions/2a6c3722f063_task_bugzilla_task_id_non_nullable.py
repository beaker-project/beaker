# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make task_bugzilla.task_id non-NULLable

Revision ID: 2a6c3722f063
Revises: 21330bf93a75
Create Date: 2017-12-20 16:43:35.364824
"""

# revision identifiers, used by Alembic.
revision = '2a6c3722f063'
down_revision = '21330bf93a75'

from alembic import op
from sqlalchemy import Integer

def upgrade():
    op.alter_column('task_bugzilla', 'task_id', existing_type=Integer, nullable=False)

def downgrade():
    op.alter_column('task_bugzilla', 'task_id', existing_type=Integer, nullable=True)
